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
    processes: list[mp.Process] = []
    n_tasks: int = 0
    
    @staticmethod
    def reset(initial_processors = False):
        TaskManager.tasks = mp.Queue()
        TaskManager.results = mp.Queue()
        if initial_processors:
            TaskManager.make_processes()
        
    @staticmethod
    def set_tasks(tasks: list[ITask]):
        for task in tasks:
            TaskManager.tasks.put(task)
        TaskManager.n_tasks = len(tasks)
    
    @staticmethod
    def make_processes():
        for i in range(TaskManager.n_processes):
            TaskManager.processes.append(mp.Process(target=TaskManager.run, args=()))
            TaskManager.processes[i].start()
    
    @staticmethod
    def run() -> None:
        while True:
            task: ITask = TaskManager.tasks.get()
            task.run()
            TaskManager.results.put(task.getResult())
    
    @staticmethod
    def get_results() -> list:
        print(TaskManager.n_tasks)
        results = []
        for i in range(TaskManager.n_tasks):
            results.append(TaskManager.results.get())
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