import re
import os
import glob
from subprocess import Popen, PIPE
from time import strftime, strptime, sleep
from contextlib import contextmanager

from telegram import InlineKeyboardButton

class BadLink(Exception):
    pass


class Video:
    def __init__(self, link, init_keyboard=False):
        self.link = link
        self.file_name = None
        self.real_file_name = None
        self.extension = None

        if init_keyboard:
            self.formats = self.get_formats()
            self.keyboard = self.generate_keyboard()

    def get_formats(self):
        formats = []

        cmd = "youtube-dl -F {}".format(self.link)# this command return the video info to string
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
        # creat subprocess,args is a string, the string is interpreted as the name or path of the program to execute
        #If shell is True, it is recommended to pass args as a string rather than as a sequence.
        #communicate() returns a tuple (stdoutdata, stderrdata).
        #communicate() Interact with process: Send data to stdin. Read data from stdout and stderr, until end-of-file is reached. Wait for process to terminate.

        it = iter(p[0].decode("utf-8", 'ignore').split('\n')) # stdoutdata split with /n in a array to a iterate
        #iter([a,b,c])

        try:
            while "code  extension" not in next(it): pass #if has not this string then goto next line
        except StopIteration:
            raise BadLink # Isn't a valid youtube link

        while True:
            try:
                line = next(it)
                if not line:
                    raise StopIteration # Usually the last line is empty
                if "video only" in line:
                    continue # I don't need video without audio
            except StopIteration:
                break
            else:
                format_code, extension, resolution, *_ = line.strip().split()
                #strip() Remove spaces at the beginning and at the end of the string
                if extension != 'webm':
                    if extension == 'm4a':
                        extension = 'm4a'
                        #extension = 'mp3'
                    formats.append([format_code, extension, resolution])
        return formats

    def generate_keyboard(self):
        """ Generate a list of InlineKeyboardButton of resolutions """
        kb = []

        for code, extension, resolution in self.formats:
            kb.append([InlineKeyboardButton("{0}, {1}".format(extension, resolution),
                                     callback_data="{0} {1}".format(code, self.link))]) #Data to be sent in a callback query to the bot, will trige CallbackQueryHandler in main.py
        return kb

    def download(self, resolution_code):
        cmd = "youtube-dl -f {0} {1}".format(resolution_code, self.link)# download video command
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()

        for line in p[0].decode("utf-8", 'ignore').split('\n'):
            if "[download] Destination:" in line:
                self.file_name = line[24:] # name of the file
            elif "has already been downloaded" in line:
                self.file_name = line[11:-28]

    def check_dimension(self):
        self.real_file_name = self.file_name.split('.')[0]
        self.extension = '.' + self.file_name.split('.')[-1]# last matched
        '''
        if self.extension == '.m4a':
            os.system('ffmpeg -i "{0}" -acodec libmp3lame -aq 6 "{1}"'.format(self.file_name, self.real_file_name + '.mp3'))
            os.remove(self.file_name)
            self.file_name = self.real_file_name + '.mp3'
            self.extension = '.mp3'
        '''
        if os.path.getsize(self.file_name) > 50 * 1024 * 1023:# big than 50mb
            os.system('split -b 49M "{0}" "{1}"'.format(self.file_name, self.real_file_name + '_'))
            #os.system() run real command in your machine

            os.remove(self.file_name)#remove orignal file

            files = glob.glob(self.real_file_name + '*')
            for file in files:
                nfile = "'" + file + "'"
                nfile_ext = "'" + file + self.extension + "'"
                cmd = 'mv ' + nfile + ' ' + nfile_ext
                os.system(cmd)

        return glob.glob(self.real_file_name + '*')# return files match in glob.glob('')

    @contextmanager #run this function with new defined send function
    def send(self):
        files = self.check_dimension() # split if size >= 50MB
        yield files

    def remove(self):
        files = glob.glob(self.real_file_name + '*')
        for f in files: #removing old files
            os.remove(f)
