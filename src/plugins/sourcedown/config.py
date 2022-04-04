from pydantic import BaseSettings


class Config(BaseSettings):
    remote_drv: str = '填写rclone远程文件夹名称'

    class Config:
        extra = "ignore"