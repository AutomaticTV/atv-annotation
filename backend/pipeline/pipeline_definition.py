import time

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.jobs import Job

class PipelineDefinition:
    class Step:
        def __init__(self, name, callback):
            self.name = name
            self.callback = callback

        def exec(self, step_name, output, *vargs):
            return self.callback(step_name, output, *vargs)

    def __init__(self, name, pipe: list):
        self.name = name
        self.pipe = pipe

    def step(self, curr_step, output, *vargs):
        c = self.pipe[curr_step]
        return c.exec(self.name, c.name, output, *vargs)

    def parse(self, curr_step):
        return PipelineExecution(self, curr_step)

class PipelineExecution:
    def __init__(self, 
        pipeline_def: PipelineDefinition,
        curr_step: int):
        self.pipeline_def = pipeline_def
        self.curr_step = curr_step

    def exec(self, on_step_end, *vargs):
        output = {}
        while self.curr_step < len(self.pipeline_def.pipe):
            output = self.pipeline_def.step(self.curr_step, output, *vargs)
            if output is not None and isinstance(output, tuple) and len(output) == 2:
                output, cancel = output
            else:
                cancel = False

            if cancel:
                return output, True
            
            self.curr_step += 1
            if on_step_end is not None:
                name = self.curr_step_name()
                on_step_end(name)
        return output, False

    def curr_step_name(self):
        if len(self.pipeline_def.pipe) <= self.curr_step:
            return 'end'
        return self.pipeline_def.pipe[self.curr_step].name