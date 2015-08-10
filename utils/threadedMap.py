from Queue import Queue
from threading import Thread
from multiprocessing import Pool


class ParalellJobs:

    def __init__(self):
        pass


def splitList(list, splitLen):
    splitted_list = []
    i = 0
    j = 0
    split = []
    for node in list:
        split.append(node)
        if (j) % (splitLen) == splitLen-1:
            splitted_list.append(split)
            split = []
            i += 1
        j += 1

    splitted_list.append(split)

    return splitted_list

def glueList(list_of_lists):
    results = []
    for list in list_of_lists:
        results.extend(list)
    return results

def proc_map(func, data, num_threads):
    workers = Pool(num_threads)
    return workers.map(func,  data)

def _thread_proc_map(func, data, num_threads, num_procs):
    node_lists = splitList(data, int(len(data)/num_procs))

    result_lists = proc_map(lambda nodes: thread_map(func, nodes, num_threads),
                            node_lists, num_procs)

    return glueList(result_lists)

def thread_map(func, data, num_threads):
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
