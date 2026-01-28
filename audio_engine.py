import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
import time
import subprocess
import json
import os

class AudioEngine:
    def __init__(self):
        self.filename = None
        self.data = None
        self.samplerate = None
        self.input_channels = 0
        self.output_channels = 2 # Default to stereo, auto-detect later
        self.stream = None
        self.current_frame = 0
        self.is_playing = False
        self.volume = 1.0
        
        self.mixing_matrix = None
        self.virtual_channels = 24 
        self.current_levels = np.zeros(self.virtual_channels)
        
        self.mute_flags = np.zeros(self.virtual_channels, dtype=bool)
        self.solo_flags = np.zeros(self.virtual_channels, dtype=bool)



        
        try:
            device_info = sd.query_devices(kind='output')
            self.output_channels = device_info['max_output_channels']
            print(f"Detected output device with {self.output_channels} channels")
        except:
            print("Could not query output device, defaulting to 2 channels")
            self.output_channels = 2

        self.scene_mode = "Standard"

    def load_file(self, filename):
        try:
            self.stop()
            self.stop()
            try:
                self.data, self.samplerate = sf.read(filename, always_2d=True)
                self.input_channels = self.data.shape[1]
                print(f"Loaded {filename} via Internal Decoder")
            except Exception as e:
                print(f"Soundfile failed ({e}), trying FFmpeg...")
                success, msg = self.load_with_ffmpeg(filename)
                if success:
                     print(f"Loaded {filename} via FFmpeg")
                else:
                    raise Exception(msg)

            self.filename = filename
            self.current_frame = 0
            
            print(f"Details: {self.samplerate}Hz, {self.input_channels}ch -> {self.output_channels}ch Out")
            
            self.reset_mapping()
            return True, "Success"
        except Exception as e:
            print(f"Error loading file: {e}")
            return False, str(e)

    def load_with_ffmpeg(self, filename):
        try:
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'stream=index,codec_name,channels,sample_rate', 
                '-select_streams', 'a', 
                '-of', 'json', 
                filename
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            info = json.loads(result.stdout)
            
            if 'streams' not in info or len(info['streams']) == 0:
                return False, "No audio streams found in file."

            errors = []
            for stream in info['streams']:
                idx = stream['index']
                codec = stream.get('codec_name', 'unknown')
                
                try:
                    channels = int(stream.get('channels', 2)) 
                    samplerate = int(stream.get('sample_rate', 44100))
                    
                    cmd_decode = [
                        'ffmpeg', 
                        '-v', 'error',
                        '-i', filename,
                        '-map', f'0:{idx}',
                        '-f', 'f32le', 
                        '-acodec', 'pcm_f32le', 
                        '-'
                    ]
                    
                    process = subprocess.Popen(cmd_decode, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    raw_audio, stderr_data = process.communicate()
                    
                    if process.returncode != 0:
                        err_msg = stderr_data.decode('utf-8', errors='ignore').strip()
                        errors.append(f"Stream #{idx} ({codec}): {err_msg}")
                        continue 
                    
                    if len(raw_audio) == 0:
                        errors.append(f"Stream #{idx} ({codec}): Decoded 0 bytes")
                        continue

                    audio_array = np.frombuffer(raw_audio, dtype=np.float32)
                    
                    if len(audio_array) % channels != 0:
                         print(f"Warning: Stream #{idx} alignment issue.")
                    
                    self.data = audio_array.reshape(-1, channels)
                    self.samplerate = samplerate
                    self.input_channels = channels
                    
                    return True, f"Loaded Stream #{idx} ({codec})"

                except Exception as ex:
                    errors.append(f"Stream #{idx} error: {str(ex)}")
                    continue
            
            return False, "All Detectable Streams Failed:\n" + "\n".join(errors)

        except FileNotFoundError:
            return False, "FFmpeg binary not found in PATH."
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def reset_mapping(self):
        self.mixing_matrix = np.zeros((self.input_channels, self.virtual_channels))
        
        min_ch = min(self.input_channels, self.virtual_channels)
        for i in range(min_ch):
            self.mixing_matrix[i][i] = 1.0
            
        if self.input_channels == 1:
            self.mixing_matrix[0][0] = 1.0 
            self.mixing_matrix[0][1] = 1.0

    def set_channel_gain(self, input_idx, output_idx, gain):
        if 0 <= input_idx < self.input_channels and 0 <= output_idx < self.virtual_channels:
            self.mixing_matrix[input_idx][output_idx] = gain

    def set_mute(self, channel_idx, state):
        if 0 <= channel_idx < self.virtual_channels:
            self.mute_flags[channel_idx] = state

    def set_solo(self, channel_idx, state):
        if 0 <= channel_idx < self.virtual_channels:
            self.solo_flags[channel_idx] = state

    def set_scene(self, scene_name):
        self.scene_mode = scene_name
        self.reset_mapping()
        
        if scene_name == "Movie":
            if self.input_channels >= 3: 
                pass
                    
        elif scene_name == "Night":
            pass

    def play(self):
        if self.data is not None and not self.is_playing:
            self.is_playing = True
            
            self.stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=self.output_channels,
                callback=self.callback,
                finished_callback=self.finished
            )
            self.stream.start()

    def pause(self):
        if self.is_playing:
            self.is_playing = False
            if self.stream:
                self.stream.stop()
                self.stream.close()

    def stop(self):
        self.pause()
        self.current_frame = 0

    def callback(self, outdata, frames, time_info, status):
        if status:
            print(f"Stream status: {status}")
        
        chunksize = min(len(self.data) - self.current_frame, frames)
        
        if chunksize <= 0:
            raise sd.CallbackStop()
        
        raw_chunk = self.data[self.current_frame : self.current_frame + chunksize]
        
        virtual_mix = np.dot(raw_chunk, self.mixing_matrix)
        
        any_solo = np.any(self.solo_flags)
        if any_solo:
            virtual_mix *= self.solo_flags
        else:
            virtual_mix *= (~self.mute_flags)
            
        if self.scene_mode == "Night":
            threshold = 0.6
            virtual_mix = np.tanh(virtual_mix / threshold) * threshold
            
        try:
            rms = np.sqrt(np.mean(virtual_mix**2, axis=0))
            self.current_levels = rms
        except:
            pass
            
        final_output = virtual_mix
        
        if self.output_channels < self.virtual_channels:
             if self.output_channels == 2:
                 downmixed = np.zeros((chunksize, 2))
                 l_sum = virtual_mix[:, 0] + virtual_mix[:, 2]*0.7 + virtual_mix[:, 3]*0.5 + virtual_mix[:, 4]*0.8 + virtual_mix[:, 6]*0.8
                 r_sum = virtual_mix[:, 1] + virtual_mix[:, 2]*0.7 + virtual_mix[:, 3]*0.5 + virtual_mix[:, 5]*0.8 + virtual_mix[:, 7]*0.8
                 
                 if self.virtual_channels > 8:
                     extras = virtual_mix[:, 8:]
                     l_extras = np.sum(extras[:, 0::2], axis=1) * 0.6
                     r_extras = np.sum(extras[:, 1::2], axis=1) * 0.6
                     
                     l_sum += l_extras
                     r_sum += r_extras
                 
                 downmixed[:, 0] = l_sum
                 downmixed[:, 1] = r_sum
                 
                 final_output = downmixed
        
        final_output *= self.volume
        
        if len(outdata) > len(final_output):
             outdata[:chunksize] = final_output
             outdata[chunksize:] = 0
             raise sd.CallbackStop()
        else:
            outdata[:] = final_output

        self.current_frame += chunksize

    def finished(self):
        self.is_playing = False
        # print("Playback finished")

    def seek(self, position_ratio):
        if self.data is not None:
             self.current_frame = int(len(self.data) * position_ratio)
