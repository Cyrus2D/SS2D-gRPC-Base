import multiprocessing as mp
import time

class ITask:
    def __init__(self) -> None:
        self.result = None
        self.done = False
    
    def _run(self) -> None:
        pass
    
    def run(self) -> None:
        self.result = self._run()
        self.done = True
        return self.result
    
    def getResult(self):
        return self.result
    
class TaskManager:
    tasks: mp.Queue = mp.Queue()
    results: mp.Queue = mp.Queue()
    n_processes: int = 20
    process: mp.Process = None
    n_tasks: int = 0
    
    @staticmethod
    def reset(initial_processors = False):
        TaskManager.tasks = mp.Queue()
        TaskManager.results = mp.Queue()
        if initial_processors:
            TaskManager.make_processes()
        
    @staticmethod
    def set_tasks(tasks: list[ITask]):
        TaskManager.tasks.put(tasks)
        TaskManager.n_tasks = 1
    
    @staticmethod
    def make_processes():
        TaskManager.process = mp.Process(target=TaskManager.run, args=())
        TaskManager.process.start()
    
    @staticmethod
    def run() -> None:
        pool = mp.Pool(TaskManager.n_processes)
        while True:
            print('getting tasks')
            tasks: ITask = TaskManager.tasks.get()
            print('got tasks')
            t = time.time()
            results = pool.map(TaskManager.run_task, tasks)
            print(f"Tasks time: {time.time() - t}")
            print('tasks done')
            TaskManager.results.put(results)
            
    @staticmethod
    def run_task(task: ITask) -> None:
        task.run()
        return task.getResult()
    
    @staticmethod
    def get_results() -> list:
        print('getting results')
        results = TaskManager.results.get()
        print('got results')
        return results
    
class OldTaskManager:
    def __init__(self, duration = -1, max_running_number = 5, tasks: ITask = None) -> None:
        self.tasks: mp.Queue[ITask] = mp.Queue()
        self.results: mp.Queue = mp.Queue()
        self.counter: int = 0
        self.processes: list[mp.Process] = []
        self.processes_number = max_running_number
        self.duration = duration
        self.start_time = time.time()
        self.n_tasks = len(tasks)
        
        if tasks is not None:
            for task in tasks:
                self.tasks.put(task)
    
    def add_task(self, task: ITask) -> None:
        self.tasks.put(task)
        
    def set_tasks(self, tasks: list[ITask]) -> None:
        for task in tasks:
            self.tasks.put(task)
    
    def run_tasks(self) -> list:
        t = time.time()
        for i in range(self.processes_number):
            self.processes.append(mp.Process(target=OldTaskManager.run_task, args=(f'P-{i}', self.tasks, self.results)))
            self.processes[i].start()
        print(f"TaskManager processes initialization time: {time.time() - t}")
        results = []
        for i in range(self.n_tasks):
            results.append(self.results.get())
        return results
    
    @staticmethod
    def run_task(name, tasks: mp.Queue, results: mp.Queue) -> None:
        while not tasks.empty():
            print('run_task')
            task: ITask = tasks.get()
            task.run()
            results.put(task.getResult())