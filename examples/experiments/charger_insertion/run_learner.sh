export XLA_PYTHON_CLIENT_PREALLOCATE=false && \
export XLA_PYTHON_CLIENT_MEM_FRACTION=.3 && \
python ../../train_rlpd.py "$@" \
    --exp_name=charger_insertion \
    --checkpoint_path=first_run \
    --demo_path=demo_data/charger_insertion_20_demos_2026-01-18_14-35-20.pkl \
    --learner \