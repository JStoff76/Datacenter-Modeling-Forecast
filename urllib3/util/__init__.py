class Retry:
    def __init__(self, total=0, backoff_factor=0, status_forcelist=None):
        self.total = total
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist or []
