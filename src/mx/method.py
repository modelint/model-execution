""" method.py -- class method """

# System
from typing import Any

# MX
from mx.activity import Activity


class Method(Activity):

    def __init__(self, anum: str, name: str, class_name: str, domain: str, instance_id: dict[str, Any]):
        super().__init__(domain=domain)
        pass

    def call(self, params: dict[str, Any]):
        pass