from collections import deque

from prof.prof_common_hexapawn import hexapawn_init_state, hexapawn_interpreter

hexapawn_states = [hexapawn_init_state]

hexapawn_queue = deque(hexapawn_states)

while hexapawn_queue:
    print("Queue:", len(hexapawn_queue), "States:", len(hexapawn_states))
    hexapawn_state = hexapawn_queue.popleft()
    for turn, state in hexapawn_interpreter.get_all_next_states(hexapawn_state):
        if state in hexapawn_states:
            continue
        hexapawn_queue.append(state)
        hexapawn_states.append(state)

print("Queue:", len(hexapawn_queue), "States:", len(hexapawn_states))
