import os
from pathlib import Path
from pydantic import BaseSettings

class Config(BaseSettings):
    remote_drv: str = '填写rclone远程文件夹名称'
    dl_root = os.path.join(Path(__file__).parent.parent.parent.parent.resolve(), 'temp')
    auto_clean_interval = 10
    mount_fld = '填写rclone mount的本地文件夹'

    class Config:
        extra = "ignore"
