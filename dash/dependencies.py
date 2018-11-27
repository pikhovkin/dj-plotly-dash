# pylint: disable=too-few-public-methods
class Output(object):
    def __init__(self, component_id, component_property):
        self.component_id = component_id
        self.component_property = component_property


# pylint: disable=too-few-public-methods
class Input(object):
    def __init__(self, component_id, component_property):
        self.component_id = component_id
        self.component_property = component_property


# pylint: disable=too-few-public-methods
class State(object):
    def __init__(self, component_id, component_property):
        self.component_id = component_id
        self.component_property = component_property


# pylint: disable=too-few-public-methods
class Event(object):
    def __init__(self, component_id, component_event):
        self.component_id = component_id
        self.component_event = component_event
