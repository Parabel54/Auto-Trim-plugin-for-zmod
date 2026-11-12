# Optional continuous native LIS2DW and cached ADC acquisition. GPL-3.0-only.
# No serial ownership, FFTs, regression, or sensor rate changes in this module.
import collections
import json
import math
import os
import queue
import shutil
import struct
import threading
import time

MAGIC = b'DCA2'
FRAME = struct.Struct('<dddd')  # native print timestamp, mapped XYZ mm/s^2
BATCH = struct.Struct('<IdII')  # frame count, host receipt, errors, overflows


def numeric(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


class AccelerationWriter:
    """Each source batch is queued once; compact binary files rotate without a pause."""
    def __init__(self, prefix, metadata, rotate_bytes=32*1024*1024,
                 max_bytes=512*1024*1024, reserve_bytes=64*1024*1024, queue_size=64):
        self.prefix, self.metadata = prefix, metadata
        self.rotate_bytes, self.max_bytes, self.reserve_bytes = rotate_bytes,max_bytes,reserve_bytes
        self.queue=queue.Queue(maxsize=queue_size)
        self.stop_event=threading.Event()
        self.error=None
        self.paths=[]
        self.samples=self.batches=self.bytes=0
        self.stream=None
        self.file_bytes=0
        self.last_timestamp=None
        self._rotate()
        self.thread=threading.Thread(target=self._run,name='deep-calibration-accel-writer',daemon=True)
        self.thread.start()

    def _rotate(self):
        if shutil.disk_usage(os.path.dirname(self.prefix)).free < self.reserve_bytes:
            raise OSError('free storage below configured reserve')
        if self.stream:
            self.stream.flush();self.stream.close();self.stream=None
        path=self.prefix+'.%04d.dca'%len(self.paths)
        header=json.dumps(dict(self.metadata,part=len(self.paths),format='<dddd',
                               batch_format='<IdII',units='mm/s^2',
                               representation='native_mapped_scaled_float64_not_ADC_integers'),
                          separators=(',',':'),allow_nan=False).encode()
        content=MAGIC+struct.pack('<I',len(header))+header
        if self.bytes+len(content)>self.max_bytes: raise OSError('acceleration byte budget exhausted')
        stream=open(path,'xb',buffering=65536)
        try: stream.write(content)
        except Exception:
            stream.close();raise
        self.stream=stream;self.paths.append(path)
        self.file_bytes=len(content);self.bytes+=len(content)

    def put(self, samples, received, errors=0, overflows=0):
        if self.error or self.stop_event.is_set(): return False
        try:
            # Source reuses/mutates its batch containers. Take a bounded copy;
            # packing and disk operations stay in this background worker.
            if len(samples)>4096: raise ValueError('oversized native acceleration batch')
            packet=(tuple(tuple(row) for row in samples),received,int(errors),int(overflows))
            self.queue.put_nowait(packet)
            return True
        except Exception as exc:
            self.error='acceleration queue/copy failure: '+type(exc).__name__+': '+str(exc)
            self.stop_event.set();return False

    def close(self): self.stop_event.set()

    def _run(self):
        try:
            while not self.stop_event.is_set() or not self.queue.empty():
                try: rows,received,errors,overflows=self.queue.get(timeout=.2)
                except queue.Empty:
                    self.stream.flush();continue
                if not rows: continue
                if not numeric(received) or errors<0 or overflows<0: raise ValueError('invalid batch metadata')
                data=bytearray(BATCH.pack(len(rows),received,errors,overflows))
                for row in rows:
                    if len(row)!=4 or not all(numeric(v) for v in row): raise ValueError('invalid acceleration frame')
                    if self.last_timestamp is not None and row[0]<=self.last_timestamp:
                        raise ValueError('acceleration timestamp repeated or reversed')
                    self.last_timestamp=row[0]
                    data.extend(FRAME.pack(*row))
                if self.bytes+len(data)>self.max_bytes: raise OSError('acceleration byte budget exhausted')
                if self.file_bytes+len(data)>self.rotate_bytes and self.file_bytes>0: self._rotate()
                if self.bytes+len(data)>self.max_bytes: raise OSError('acceleration byte budget exhausted')
                self.stream.write(data);self.file_bytes+=len(data);self.bytes+=len(data)
                self.samples+=len(rows);self.batches+=1
                if self.batches%10==0:self.stream.flush()
        except Exception as exc:
            self.error='acceleration writer failure: '+str(exc)
        finally:
            self.stop_event.set()
            if self.stream:
                try:self.stream.flush();self.stream.close()
                except Exception as exc:self.error='acceleration close failure: '+str(exc)


def read_acceleration(paths):
    """Streaming reader; fails on truncated/corrupt records, never fills RAM."""
    previous=None
    expected_part=0
    identity=None
    for path in paths:
        with open(path,'rb') as stream:
            if stream.read(4)!=MAGIC:raise ValueError('invalid acceleration magic')
            size=stream.read(4)
            if len(size)!=4:raise ValueError('truncated acceleration header')
            size=struct.unpack('<I',size)[0]
            if size>65536:raise ValueError('oversized acceleration header')
            encoded=stream.read(size)
            if len(encoded)!=size:raise ValueError('truncated acceleration metadata')
            meta=json.loads(encoded)
            if meta.get('part')!=expected_part:raise ValueError('missing/out-of-order acceleration part')
            if identity is None:identity=meta.get('session')
            elif meta.get('session')!=identity:raise ValueError('mixed acceleration sessions')
            expected_part+=1
            while True:
                head=stream.read(BATCH.size)
                if not head:break
                if len(head)!=BATCH.size:raise ValueError('truncated acceleration batch')
                n,received,errors,overflows=BATCH.unpack(head)
                if not 1<=n<=4096 or not numeric(received):raise ValueError('invalid acceleration batch')
                for i in range(n):
                    blob=stream.read(FRAME.size)
                    if len(blob)!=FRAME.size:raise ValueError('truncated acceleration frame')
                    row=FRAME.unpack(blob)
                    if not all(numeric(v) for v in row):raise ValueError('non-finite acceleration frame')
                    if previous is not None and row[0]<=previous:raise ValueError('non-increasing acceleration time')
                    previous=row[0]
                    yield dict(t=row[0],x=row[1],y=row[2],z=row[3],host_received=received,
                               errors=errors,overflows=overflows)


class SensorExtension:
    def __init__(self, owner, config):
        self.owner=owner;self.printer=owner.printer;self.reactor=owner.reactor
        self.accel_name=config.get('accelerometer','lis2dw')
        self.adc_format=config.get('adc_callback_format','batch')
        if self.adc_format not in ('batch','scalar'):
            raise config.error('deep_calibration: adc_callback_format must be batch or scalar')
        self.accel_default=config.getint('accel_default',1,minval=0,maxval=1)
        self.adc_default=config.getint('adc_default',1,minval=0,maxval=1)
        self.rotate_bytes=config.getint('accel_rotate_mb',32,minval=1,maxval=256)*1024*1024
        self.max_bytes=config.getint('accel_max_mb',512,minval=1,maxval=4096)*1024*1024
        self.reserve_bytes=config.getint('storage_reserve_mb',64,minval=16,maxval=1024)*1024*1024
        self.helper=self.writer=None
        self.attached=False
        self.accel_enabled=self.adc_enabled=False
        self.channels={};self.adc_last={}
        self.adc_hooks=[];self.adc_attached=False
        self.adc_pending=collections.deque(maxlen=2048)
        self.adc_lock=threading.Lock()
        self.adc_received={}
        # Temperature channels are context: an irregular report is recorded
        # and skipped, a silent channel is recorded as lost; neither stops
        # the load cell and acceleration capture.
        self.adc_anomalies={};self.adc_lost=set()
        self.last_batch_time=None;self.begin=0.
        self.batches_received=self.frames_received=0
        self.callback_max_seconds=0.
        self.error=None
        self.starting=False
        self.stopping=False
        self.callback=self._batch

    def configure(self,gcmd):
        flags=[]
        for key,default in (('ACCEL',self.accel_default),('ADC',self.adc_default)):
            value=gcmd.get_float(key,default,minval=0,maxval=1)
            if value not in (0.,1.):raise gcmd.error('DEEP CALIBRATION: '+key+' must be 0 or 1')
            flags.append(bool(value))
        if self.writer and self.writer.thread.is_alive():raise gcmd.error('DEEP CALIBRATION: previous acceleration writer still finishing')
        if self.attached:raise gcmd.error('DEEP CALIBRATION: previous acceleration client still attached')
        self.accel_enabled,self.adc_enabled=flags
        self.error=None;self.helper=None;self.channels={};self.adc_last={}
        self.adc_received={};self.adc_pending.clear();self.adc_hooks=[]
        self.adc_anomalies={};self.adc_lost=set()
        self.writer=None;self.batches_received=self.frames_received=0;self.last_batch_time=None
        self.callback_max_seconds=0.
        if self.accel_enabled:
            chip=self.printer.lookup_object(self.accel_name,None)
            self.helper=getattr(chip,'batch_bulk',None)
            if (self.helper is None or not callable(getattr(self.helper,'add_client',None))
                    or not isinstance(getattr(self.helper,'client_cbs',None),list)
                    or not callable(getattr(self.helper,'_stop',None))):
                raise gcmd.error('DEEP CALIBRATION: unsupported native bulk interface for '+self.accel_name)
            if getattr(chip,'data_rate',None)!=1600:
                raise gcmd.error('DEEP CALIBRATION: this adapter targets the verified LIS2DW 1600 Hz interface')
        if self.adc_enabled:
            query=self.printer.lookup_object('query_adc',None)
            registry=getattr(query,'adc',None)
            if not isinstance(registry,dict) or not registry:
                raise gcmd.error('DEEP CALIBRATION: native query_adc registry unavailable')
            self.channels={name:obj for name,obj in registry.items()
                           if hasattr(obj,'_callback') and getattr(obj,'_sample_count',1)>0}
            if not self.channels or len(self.channels)>64:
                raise gcmd.error('DEEP CALIBRATION: expected 1..64 configured ADC channels')
        return dict(acceleration=self.accel_enabled,adc=self.adc_enabled,adc_channels=list(self.channels),
                    adc_report_intervals={name:getattr(adc,'_report_time',None) for name,adc in self.channels.items()},
                    adc_callback_format=self.adc_format,accelerometer=self.accel_name,
                    acquisition='continuous_until_session_end_no_windows',
                    acceleration_format='mapped_scaled_float64_mm_s2',
                    acceleration_max_bytes=self.max_bytes,acceleration_rotate_bytes=self.rotate_bytes)

    def start(self,prefix):
        self.begin=self.reactor.monotonic()
        self.starting=True
        try:
            if self.adc_enabled:self._attach_adc()
            if self.accel_enabled:
                self.writer=AccelerationWriter(prefix+'.accel',dict(session=os.path.basename(prefix),sensor=self.accel_name,
                                                                   data_rate=1600,clock='MCU print_time'),
                                               self.rotate_bytes,self.max_bytes,self.reserve_bytes)
                # Rotation never changes measurement state or other clients.
                self.attached=True
                self.helper.add_client(self.callback)
            self.begin=self.reactor.monotonic()
        except Exception:
            self.stop();raise
        finally:
            self.starting=False

    def _batch(self,message):
        began=time.perf_counter()
        try:
            if not self.owner.active or not self.accel_enabled:return False
            rows=message.get('data',())
            errors=message.get('errors',0);overflows=message.get('overflows',0)
            if errors or overflows:
                self.error='native acceleration errors/overflows: %s/%s'%(errors,overflows)
                return False
            if rows:
                if not self.writer.put(rows,self.reactor.monotonic(),errors,overflows):
                    self.error=self.writer.error or 'acceleration writer stopped';return False
                self.last_batch_time=self.reactor.monotonic()
                self.batches_received+=1;self.frames_received+=len(rows)
            return True
        except Exception as exc:
            self.error='acceleration callback failure: '+str(exc);return False
        finally:
            self.callback_max_seconds=max(self.callback_max_seconds,time.perf_counter()-began)

    def tick(self,now):
        if not self.owner.active or self.starting:return
        if self.writer and self.writer.error:self.error=self.writer.error
        if self.accel_enabled and now-(self.last_batch_time if self.last_batch_time is not None else self.begin)>2.:
            self.error=self.error or 'acceleration stream stale or absent for more than 2 s'
        if self.error:raise RuntimeError(self.error)
        if self.adc_enabled:self._drain_adc(now)

    def _adc_anomaly(self,name,kind,**fields):
        self.adc_anomalies[kind]=self.adc_anomalies.get(kind,0)+1
        self.owner._event('adc_'+kind,channel=name,**fields)

    def _drain_adc(self,now):
        with self.adc_lock:
            pending=list(self.adc_pending);self.adc_pending.clear()
        for name,received,stamp,value in pending:
            if not numeric(stamp) or not numeric(value) or not 0<=value<=1 or stamp<=0:
                self._adc_anomaly(name,'report_skipped',reason='invalid',received=received);continue
            previous=self.adc_last.get(name)
            if previous is not None and stamp<=previous:
                self._adc_anomaly(name,'report_skipped',reason='repeated_or_reversed',received=received,print_time=stamp);continue
            interval=getattr(self.channels[name],'_report_time',None)
            if previous is not None and numeric(interval) and interval>0 and stamp-previous>1.5*interval:
                self._adc_anomaly(name,'gap',from_print_time=previous,to_print_time=stamp,
                                  gap_s=stamp-previous,expected_s=interval)
            adc=self.channels[name]
            age=adc.get_mcu().estimated_print_time(received)-stamp
            if not numeric(age) or age < -1. or age>2.:
                self._adc_anomaly(name,'report_skipped',reason='clock_or_latency',received=received,print_time=stamp);continue
            self.adc_last[name]=stamp;self.adc_received[name]=received
            if name in self.adc_lost:
                self.adc_lost.discard(name);self._adc_anomaly(name,'channel_resumed',received=received)
            accepted=self.owner._write(dict(type='adc',channel=name,t=received,print_time=stamp,
                                   normalized_value=value,age=age,callback_format=self.adc_format,
                                   representation='native_normalized_aggregate_not_individual_conversions'))
            if not accepted:raise RuntimeError('ADC log writer stopped')
        for name in self.channels:
            if name not in self.adc_lost and now-self.adc_received.get(name,self.begin)>2.:
                self.adc_lost.add(name);self._adc_anomaly(name,'channel_lost',silent_s=now-self.adc_received.get(name,self.begin))

    def _attach_adc(self):
        self.adc_attached=True
        for name,adc in self.channels.items():
            original=adc._callback
            def observer(*args,_name=name,_original=original):
                # Always execute native temperature/safety handling. Its errors
                # propagate exactly as before; recorder errors never suppress it.
                result=_original(*args) if _original is not None else None
                if self.owner.active and self.adc_attached:
                    try:
                        if self.adc_format=='batch':
                            if len(args)!=1:raise ValueError('expected batched ADC callback')
                            rows=args[0]
                        else:
                            if len(args)!=2:raise ValueError('expected scalar ADC callback')
                            rows=[args]
                        if len(rows)>512:raise ValueError('oversized native ADC batch')
                        received=self.reactor.monotonic()
                        with self.adc_lock:
                            for row in rows:
                                if len(row)!=2:raise ValueError('expected timestamp/value ADC pair')
                                if len(self.adc_pending)==self.adc_pending.maxlen:
                                    raise ValueError('ADC queue overflow')
                                self.adc_pending.append((_name,received,row[0],row[1]))
                    except Exception as exc:
                        self.error='ADC observer failure: '+str(exc)
                return result
            adc._callback=observer
            self.adc_hooks.append((adc,original,observer))

    def stop(self):
        if self.stopping:return
        self.stopping=True
        self.adc_attached=False
        for adc,original,observer in self.adc_hooks:
            if adc._callback is observer:adc._callback=original
        self.adc_hooks=[]
        if self.adc_enabled and self.owner.active:
            try:self._drain_adc(self.reactor.monotonic())
            except Exception as exc:self.error=self.error or 'ADC final drain failed: '+str(exc)
        # Native helper has no public remove_client. Remove exactly our callback
        # through the verified client list, stopping the driver only if no other
        # consumers remain. Do not call _stop when someone else is subscribed.
        if self.helper is not None and self.attached:
            try:
                if self.callback in self.helper.client_cbs:
                    self.helper.client_cbs.remove(self.callback)
                    if not self.helper.client_cbs and self.helper.is_started:self.helper._stop()
            except Exception as exc:
                self.error=self.error or 'native acceleration cleanup failed: '+str(exc)
            finally:
                self.attached=False
        if self.writer:self.writer.close()
        self.stopping=False

    def status(self):
        return dict(acceleration=self.accel_enabled,adc=self.adc_enabled,adc_channels=list(self.channels),
                    adc_callback_format=self.adc_format,adc_attached=self.adc_attached,
                    adc_report_timestamps=dict(self.adc_last),attached=self.attached,error=self.error,
                    adc_anomalies=dict(self.adc_anomalies),adc_lost=sorted(self.adc_lost),
                    batches_received=self.batches_received,frames_received=self.frames_received,
                    callback_max_seconds=self.callback_max_seconds,
                    last_batch_host_time=self.last_batch_time,
                    acceleration_paths=list(self.writer.paths) if self.writer else [],
                    acceleration_samples_written=self.writer.samples if self.writer else 0,
                    acceleration_bytes_written=self.writer.bytes if self.writer else 0,
                    acceleration_writer_alive=self.writer.thread.is_alive() if self.writer else False,
                    acceleration_writer_error=self.writer.error if self.writer else None)
