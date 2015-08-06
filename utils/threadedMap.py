from Queue import Queue
from threading import Thread

class ParalellJobs:

    def __init__(self):
        pass


def conc_map(func, data, num_threads):
    def do_stuff(q, r):
      while not q.empty():
        r.put(func(q.get()))
        q.task_done()

    q = Queue(maxsize=len(data))
    r = Queue(maxsize=len(data))

    for x in data:
      q.put(x)

    for i in range(num_threads):
      worker = Thread(target=do_stuff, args=(q,r,))
      worker.setDaemon(True)
      worker.start()

    q.join()

    return [item for item in r.queue]



#print conc_map(lambda x: x*x, range(20), 3)