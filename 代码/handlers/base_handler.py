class BaseHandler:
    def __init__(self, config):
        self.config = config

    def process(self, episode, danmaku_list, known_roles) -> dict:
        raise NotImplementedError