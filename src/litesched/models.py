import msgspec


class UpdateTimer(msgspec.Struct, tag=True):
    job_id: str
    cron: str


class RemoveTimer(msgspec.Struct, tag=True):
    job_id: str


class AddTimer(msgspec.Struct, tag=True):
    job_id: str
    cron: str
