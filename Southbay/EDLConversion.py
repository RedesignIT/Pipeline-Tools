import re
import os
import sys
import csv


class EDLConversion:
    def __init__(self):
        self.SOURCE = 'Final'
        self.FRAMERATE = 24
        self.FRAMESTART = 990
        self.FRAMEHANDLE = 10
        self.EDL = r"C:\Users\Wade\Desktop\Sc090_TURNOVER_FIXED.edl"
        # self.EDL = sys.argv[1]
        self.CSV_VALUES = [
            'Shot Code', 'Client Source File', 'Source', 'slopeR', 'slopeG', 'slopeB', 'offsetR', 'offsetG', 'offsetB',
            'powerR', 'powerG', 'powerB', 'Sat', 'Cut Duration', 'Cut In', 'Cut Out'
        ]
        self.REGEX = {
            'package': r'(\|\d{6}.*?\*SO\S[^|]+)',
            'number': r'\|(\d{6})',
            'time': r'(\d{1,2}:\d{1,2}:\d{1,2}:\d{1,3})',
            'name': r'SHOT=(.*?)\|',
            'cdl': r'([\-0-9]{1,2}\.\d{4})',
            'sat': r'SAT ([\.0-9]{1,7})',
            'source': r'FILE: (\S+)'
        }
        self.number = None

    def open_edl(self):
        with open(self.EDL, 'r') as edl:
            edl_data = edl.read().replace('\n', '|')

        regex = re.compile(self.REGEX['package'])
        shots_list = re.findall(regex, edl_data)
        return shots_list

    def compile_dicts(self):
        shots = dict()
        shots_list = self.open_edl()
        for item in shots_list:
            regex = re.compile(self.REGEX['number'])
            number = re.findall(regex, item)[0]
            shots[number] = self.create_dict(item)
            if self.number is None:
                self.number = number
        return shots

    def create_dict(self, shot):
        shot_dict = dict()
        cdl_list = list()

        regex = re.compile(self.REGEX['name'])
        shot_dict['Shot Code'] = (str(re.findall(regex, shot)[0]).rstrip()).replace(" ", "_")

        regex = re.compile(self.REGEX['source'])
        shot_dict['Client Source File'] = str(re.findall(regex, shot)[0])

        shot_dict['Source'] = self.SOURCE

        regex = re.compile(self.REGEX['cdl'])
        cdl_data = re.findall(regex, shot)
        if len(cdl_data) == 9:
            for value in cdl_data:
                cdl_list.append(value)
        else:
            cdl_list = ['1.0000', '1.0000', '1.0000', '0.0000', '0.0000', '0.0000', '1.0000', '1.0000', '1.0000']
        shot_dict.update(dict(zip(self.CSV_VALUES[3:12], cdl_list)))

        regex = re.compile(self.REGEX['sat'])
        sat_search = re.findall(regex, shot)
        if len(sat_search) == 1:
            sat = sat_search[0]
        else:
            sat = '1'
        shot_dict['Sat'] = format(float(sat), '.5f')

        regex = re.compile(self.REGEX['time'])
        time = re.findall(regex, shot)
        conversion = TCConversion(self.FRAMERATE, handle_size=self.FRAMEHANDLE, frame_start=self.FRAMESTART)
        frames = conversion.tcrange_to_framerange(time[0], time[1])
        frames = [int(x) for x in frames]
        shot_dict['Cut Duration'] = str((frames[1] - frames[0]) + 1)
        shot_dict['Cut In'] = str(frames[0])
        shot_dict['Cut Out'] = str(frames[1])

        return shot_dict

    def create_csv(self, edl_data):
        if self.number is not None:
            count = int(self.number)
        else:
            sys.stderr.write('Nothing to write')
            sys.exit(1)
        csvfile = os.path.splitext(self.EDL)[0] + '.csv'
        with open(csvfile, 'wb') as f:
            w = csv.writer(f)
            w.writerow(self.CSV_VALUES)
            while count <= len(edl_data):
                items = []
                shot = edl_data[str(count).zfill(6)]
                for item in self.CSV_VALUES:
                    items.append(shot[item])
                w.writerow(items)
                count += 1


class TCConversion:
    def __init__(self, framerate, handle_size=0, frame_start=0, tc_start=None):
        self.framerate = float(framerate)
        self.handle_size = handle_size
        self.frame_start = frame_start
        self.tc_start = tc_start

    def tcrange_to_framerange(self, tc_start, tc_end):
        start_frames = self.tc_to_frames(tc_start)
        end_frames = self.tc_to_frames(tc_end)
        if self.frame_start > 0:
            start = self.frame_start
            end = (end_frames - start_frames - 1) + start + (self.handle_size * 2)
        else:
            start = start_frames
            end = (end_frames - 1)
        return start, end

    def framerange_to_tcrange(self, frame_start, frame_end):
        start_tc = self.frames_to_tc(frame_start)
        end_tc = self.frames_to_tc(frame_end)
        if self.tc_start is not None:
            start = self.tc_start
            start_frames = self.tc_to_frames(self.tc_start)
            end_frames = (start_frames + ((frame_end - frame_start) - (self.handle_size * 2)))
            end = self.frames_to_tc(end_frames + 1)
        else:
            start = start_tc
            end = end_tc
        return start, end

    def tc_to_frames(self, tc):
        tc = tc.split(':')
        tc = [int(x) for x in tc]
        frames = (((tc[0] * 3600) + (tc[1] * 60) + tc[2]) * self.framerate) + tc[3]
        return frames

    def frames_to_tc(self, frames):
        time = frames / self.framerate
        hours = int(time / 3600)
        mins = int((time % 3600) / 60)
        secs = int(time % 60)
        xframes = int(frames % self.framerate)
        tc = "{0:02d}:{1:02d}:{2:02d}:{3:02d}".format(hours, mins, secs, xframes)
        return tc


if __name__ == '__main__':
    edlc = EDLConversion()
    data = edlc.compile_dicts()
    edlc.create_csv(data)
