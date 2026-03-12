import multiprocessing
from time import sleep

def test_loop(tq, se):
    print("started test loop")
    while not se.is_set():
        pass
    print("stopped test loop")

test_queue = multiprocessing.Queue(maxsize=10)
stop_event = multiprocessing.Event()

if __name__ == "__main__":
    process = multiprocessing.Process(target=test_loop, args=(test_queue, stop_event))
    process.start()
    sleep(3)
    stop_event.set()
    process.join()