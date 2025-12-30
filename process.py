import time
import numpy as np
from trainer_process_example import trainer_process, COMPLETE_STATE_SEQUENCE, INACTIVE_THRESH
from state_tracker import StateTracker

state_tracker = StateTracker(COMPLETE_STATE_SEQUENCE, INACTIVE_THRESH)

def process(frame_instance):
    frame_width = frame_instance.get_frame_width()
    frame_height = frame_instance.get_frame_height()

    # Process the image.
    state_tracker.before_process()
    if frame_instance.validate():
        trainer_process(frame_instance, state_tracker, frame_width, frame_height)
        state_tracker.after_process(frame_instance)
    else:
        state_tracker.after_process(frame_instance)
        state_tracker.reset()

    return frame_instance.get_frame()