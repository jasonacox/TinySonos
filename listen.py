from queue import Empty
from soco.events import event_listener
import logging
logging.basicConfig()
import soco
from pprint import pprint
from soco.events import event_listener
# pick a device at random and use it to get
# the group coordinator
device = soco.discover().pop().group.coordinator
print (device.player_name)
sub = device.renderingControl.subscribe()
sub2 = device.avTransport.subscribe()

while True:
    try:
        event = sub.events.get(timeout=0.5)
        pprint ("** renderingControl **")
        pprint (event.variables)
        # {'volume': {'LF': '100', 'Master': '6', 'RF': '100'}}
    except Empty:
        pass
    try:
        event = sub2.events.get(timeout=0.5)
        pprint ("** avTransport **")
        pprint (event.variables)
        # 'transport_state': 'PAUSED_PLAYBACK
        # 'transport_state': 'TRANSITIONING'
        # 'transport_state': 'PLAYING'
    except Empty:
        pass

    except KeyboardInterrupt:
        sub.unsubscribe()
        sub2.unsubscribe()
        event_listener.stop()
        break

