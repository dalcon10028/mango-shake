import dataclasses


class BaseWsReq:

    def __init__(self, op, args):
        self.op = op
        self.args = args


@dataclasses.dataclass
class SubscribeReq:

    def __init__(self, inst_type, channel, inst_id):
        self.inst_type = inst_type
        self.channel = channel
        self.inst_id = inst_id

    def __eq__(self, other) -> bool:
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(self.inst_type + self.channel + self.inst_id)


class WsLoginReq:

    def __init__(self, api_key, passphrase, timestamp, sign):
        self.api_key = api_key
        self.passphrase = passphrase
        self.timestamp = timestamp
        self.sign = sign
