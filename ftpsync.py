#!/usr/bin/env python3.2

import ftplib
import configparser
import sys
import string
import posixpath
import os
import io
import time

class Syncer:

    def __init__(self, config):
        self.config = config
        self.ftp = ftplib.FTP(config['REMOTE']['host'])

        self.TIMEFILE = ".ftpsync.temporary.timefile"

        try:
            ok = self.ftp.login(config['REMOTE']['user'], config['REMOTE']['pass'])
            print(ok)
        except ftplib.error_perm as e:
            print(e)
            sys.exit(1)

    def remote_time(self):
        """ return the remote time

            creates a temporary file on the FTP server to read its modification
            date
        """
        try:
            self.ftp.cwd(config['REMOTE']['dir'])
            self.ftp.storbinary('STOR '+self.TIMEFILE, io.StringIO(""))
            mtime = self.ftp.sendcmd('MDTM '+self.TIMEFILE).split(' ')
            mtime = mtime[1]
            self.ftp.sendcmd('DELE '+self.TIMEFILE)
        except ftplib.error_perm as e:
            print(e)
            mtime = 0
        return time.mktime(time.strptime(mtime,'%Y%m%d%H%M%S'))

    def local_time(self):
        """ return the local time
        """
        return time.mktime(time.gmtime())


    def remote_filelist(self, base, dir):
        print("reading [REMOTE]%s" %posixpath.join(base,dir))

        ls = []
        try:
            self.ftp.cwd(posixpath.join(base,dir))
            self.ftp.retrlines('MLSD', ls.append)
        except ftplib.error_perm as e:
            print("Failed to retrieve remote file list: %s" % e)
            sys.exit(1)

        items = []
        for line in ls:
            item = self.parse_ftpls(line,dir)
            if(item['type'] == 'dir'):
                items.append(item)
                items += self.remote_filelist(base, item['file'])
            elif(item['type'] == 'file'):
                items.append(item)
            else:
                # others are parent and current dir
                None

        return items

    def local_filelist(self, base, dir):
        print("reading [LOCAL]%s" % os.path.join(base,dir))

        items = []

        for file in os.listdir(os.path.join(base,dir)):
            full = os.path.join(base,dir,file);
            item = {}
            item['file']   = os.path.join(dir,file)
            item['modify'] = os.path.getmtime(full)
            if(os.path.isdir(full)):
                item['type'] = 'dir'
                items += self.local_filelist(base, os.path.join(dir,file))
            else:
                item['type'] = 'file'
            stat = os.lstat(full)
            item['UNIX.mode'] = stat.st_mode
            items.append(item)

        return items


    def parse_ftpls(self,line,dir):
        item = {}
        parts = line.split('; ',2)
        item['file'] = posixpath.join(dir,parts[1])
        parts = parts[0].split(';')
        for part in parts:
            opts = part.split('=',2)
            item[opts[0]] = opts[1]

        # convert to unix timestamp
        item['modify'] = time.mktime(time.strptime(item['modify'],'%Y%m%d%H%M%S'))

        return item


if __name__ == "__main__":
    # fixme move this to the constructor of Syncer
    config = configparser.ConfigParser()
    config.read(['test.ini'])

    syncer = Syncer(config)

    # fixme consolidate all this in a Syncer.sync method
    print(syncer.remote_time())
    print(syncer.local_time())
    items = syncer.remote_filelist(config.get('REMOTE','dir'),'')
    print(items)
    items = syncer.local_filelist(config.get('LOCAL','dir'),'')
    print(items)

    # FIXME first test for writing back the config
    config['TIMES'] ={ 'remote_start': 123 }
    with open('test.ini', 'w') as configfile:
       config.write(configfile)

