import subprocess

from .groupList import yellow_book
from . import config

remote_drv = config.remote_drv

class Manager:
    @staticmethod
    def retrieveRemoteFolderLink(group_id):
        remote_path = Manager.selectRmtFolder(group_id)
        return Manager.retrieveLink(remote_path)

    @staticmethod
    def selectRmtFolder(group_id):
        remote_path = yellow_book.get(group_id)
        if not remote_path:
            remote_path = '杂货'
        return remote_drv + remote_path

    @staticmethod
    def retrieveLink(remote_path):
        proc = subprocess.run(['rclone', 'link', remote_path], stdout=subprocess.PIPE)
        if proc.returncode == 0:
            return proc.stdout.decode('utf-8')
        return False

    @staticmethod
    def mkRemoteDir(remote_path):
        proc = subprocess.run(['rclone', 'mkdir', '{}{}'.format(remote_drv, remote_path)])
        if proc.returncode == 0:
            return True
        return False