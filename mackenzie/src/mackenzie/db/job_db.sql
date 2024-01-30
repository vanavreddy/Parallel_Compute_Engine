# Slurm job database

-- module: job_db
-- schema: job

create table if not exists job (
    job_id text primary key,
    job_type text not null,
    job_data text not null,
    job_priority text not null,

    sbatch_script text not null,
    load int not null,
    max_fails int not null,

    job_result text,

    slurm_job_id bigint,
    job_state text not null,
    failure_count int not null
);

-- schema: job_state

create index if not exists job_state on job (job_state) ;

-- schema: slurm_job

create table if not exists slurm_job (
    slurm_job_id int primary key,
    job_id text not null,

    start_time bigint not null,
    end_time bigint,
    sacct_info text
);

-- schema: slurm_job_id

create index if not exists slurm_job_job_id on slurm_job (job_id);

-- query: add_job
-- params: job_id: str!, job_type: str!, job_data: str!, job_priority: int!, sbatch_script: str!, load: int!, max_fails: int!

insert into job values (
    :job_id, :job_type, :job_data, :job_priority,
    :sbatch_script, :load, :max_fails,
    null,
    null, 'ready', 0
);

-- query: set_job_ready
-- params: job_id: str!, sbatch_script: str!

update job
set sbatch_script = :sbatch_script, job_state = 'ready'
where job_id = :job_id ;

-- query: set_job_running
-- params: job_id: str!, slurm_job_id: int!

update job
set job_state = 'running', slurm_job_id = :slurm_job_id
where job_id = :job_id ;

-- query: set_job_failed
-- params: job_id: str!

update job
set job_state = 'failed', failure_count = failure_count + 1
where job_id = :job_id ;

-- query: set_job_completed
-- params: job_id: str!, job_result: str!

update job
set job_state = 'completed' and job_result = :job_result
where job_id = :job_id ;

-- query: set_job_processed
-- params: job_id: str!

update job
set job_state = 'processed'
where job_id = :job_id ;

-- query: set_job_aborted
-- params: job_id: str!

update job
set job_state = 'aborted'
where job_id = :job_id ;

-- query: add_slurm_job
-- params: slurm_job_id: int!, job_id: int!, start_time: int!

insert into slurm_job values (
    :slurm_job_id, :job_id, :start_time,
    null, null
);

-- query: set_slurm_job_completion_info
-- params: slurm_job_id: int!, end_time: int!, sacct_info: str!

update slurm_job
set end_time = :end_time and sacct_info = :sacct_info
where slurm_job_id = :slurm_job_id ;

-- query: count_live_jobs
-- return?: live_job_count: int

select count(*)
from job
where job_state in ('ready','running','failed') ;

-- query: get_running_load
-- return?: running_load: int

select sum(load)
from job
where job_state = 'running' ;

-- query: get_live_load
-- return?: live_load: int

select sum(load)
from job
where job_state in ('running', 'ready', 'failed') ;

-- query: get_running_jobs
-- return*: job_id: str!, job_type: str!, job_data: str!, slurm_job_id: int

select job_id, job_type, job_data, slurm_job_id
from job
where job_state = 'running' ;

-- query: get_failed_jobs
-- return*: job_id: str!, job_type: str!, job_data: str!, failure_count: int!, max_fails: int!

select job_id, job_type, job_data, failure_count, max_fails
from job
where job_state = 'failed' ;

-- query: get_ready_jobs
-- return*: job_id: str!, sbatch_script: str!, load: int!

select job_id, sbatch_script, load
from job
where job_state = 'ready'
order by job_priority desc, load desc, job_id asc ;
