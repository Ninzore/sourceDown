from pydantic import BaseSettings

class Config(BaseSettings):
    remote_drv: str = '填写rclone远程文件夹名称'
    auto_clean_interval = 10

    class Config:
        extra = "ignore"
