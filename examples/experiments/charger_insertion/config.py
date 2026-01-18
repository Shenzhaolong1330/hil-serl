import os
import jax
import jax.numpy as jnp
import numpy as np

from franka_env.envs.wrappers import (
    Quat2EulerWrapper,
    SpacemouseIntervention,
    MultiCameraBinaryRewardClassifierWrapper,
    GripperCloseEnv
)
from franka_env.envs.relative_env import RelativeFrame
from franka_env.envs.franka_env import DefaultEnvConfig
from serl_launcher.wrappers.serl_obs_wrappers import SERLObsWrapper
from serl_launcher.wrappers.chunking import ChunkingWrapper
from serl_launcher.networks.reward_classifier import load_classifier_func

from experiments.config import DefaultTrainingConfig
from experiments.charger_insertion.wrapper import ChargerInsertionEnv

class EnvConfig(DefaultEnvConfig):
    SERVER_URL = "http://192.168.110.15:5000/"
    REALSENSE_CAMERAS = {
        "wrist": {
            "serial_number": "344322074412",
            "dim": (1280, 720),
            "exposure": 40000,
        },
        "side": {
            "serial_number": "243322071821",
            "dim": (1280, 720),
            "exposure": 40000,
        },
    }
    # 图像裁剪区域，需要根据任务定制
    IMAGE_CROP = {
        "wrist": lambda img: img[150:600, 450:1150],
        "side": lambda img: img[100:400, 400:850],
    }
    # 任务完成时的位置，需要根据任务定制
    TARGET_POSE = np.array([0.41069017934252483,-0.02949999833602605,0.048396183874899384,3.118876581253268,-0.03125725971178328,1.560604549287991])
    # 任务开始抓取物体的位置，需要根据任务定制
    GRASP_POSE = np.array([[0.41069017934252483,-0.02949999833602605,0.048396183874899384,3.118876581253268,-0.03125725971178328,1.560604549287991]])
    # 重置位置，需要根据任务定制
    RESET_POSE = TARGET_POSE + np.array([0, 0, 0.07, 0, 0.05, 0])
    # 安全框，需要根据任务定制
    ABS_POSE_LIMIT_LOW = TARGET_POSE - np.array([0.5, 0.5, 0.5, 0.1, 0.1, 0.4])
    ABS_POSE_LIMIT_HIGH = TARGET_POSE + np.array([0.5, 0.5, 0.5, 0.1, 0.1, 0.4])
    RANDOM_RESET = True
    RANDOM_XY_RANGE = 0.02
    RANDOM_RZ_RANGE = 0.05
    ACTION_SCALE = (0.03, 0.1, 1)
    DISPLAY_IMAGE = True
    MAX_EPISODE_LENGTH = 80

    COMPLIANCE_PARAM = {
        # "translational_stiffness": 2000,
        # "translational_damping": 89,
        # "rotational_stiffness": 150,
        # "rotational_damping": 7,
        # "translational_Ki": 0.05,
        # "translational_clip_x": 0.0075,
        # "translational_clip_y": 0.0075,
        # "translational_clip_z": 0.005,
        # "translational_clip_neg_x": 0.0075,
        # "translational_clip_neg_y": 0.0075,
        # "translational_clip_neg_z": 0.005,
        # "rotational_clip_x": 1.0,
        # "rotational_clip_y": 1.0,
        # "rotational_clip_z": 1.0,
        # "rotational_clip_neg_x": 1.0,
        # "rotational_clip_neg_y": 1.0,
        # "rotational_clip_neg_z": 1.0,
        # "rotational_Ki": 0.05,
        "translational_stiffness": 2200,
        "translational_damping": 89,
        "rotational_stiffness": 260,
        "rotational_damping": 9,
        "translational_Ki": 0.05,
        "translational_clip_x": 0.01,
        "translational_clip_y": 0.01,
        "translational_clip_z": 0.01,
        "translational_clip_neg_x": 0.01,
        "translational_clip_neg_y": 0.01,
        "translational_clip_neg_z": 0.01,
        "rotational_clip_x": 0.05,
        "rotational_clip_y": 0.05,
        "rotational_clip_z": 0.05,
        "rotational_clip_neg_x": 0.05,
        "rotational_clip_neg_y": 0.05,
        "rotational_clip_neg_z": 0.05,
        "rotational_Ki": 0.05,
    }
    PRECISION_PARAM = {
        "translational_stiffness": 2000,
        "translational_damping": 89,
        "rotational_stiffness": 150,
        "rotational_damping": 7,
        "translational_Ki": 0.0,
        "translational_clip_x": 0.01,
        "translational_clip_y": 0.01,
        "translational_clip_z": 0.01,
        "translational_clip_neg_x": 0.01,
        "translational_clip_neg_y": 0.01,
        "translational_clip_neg_z": 0.01,
        "rotational_clip_x": 0.03,
        "rotational_clip_y": 0.03,
        "rotational_clip_z": 0.03,
        "rotational_clip_neg_x": 0.03,
        "rotational_clip_neg_y": 0.03,
        "rotational_clip_neg_z": 0.03,
        "rotational_Ki": 0.0,
    }

class TrainConfig(DefaultTrainingConfig):
    image_keys = ["wrist", "side"]
    classifier_keys = ["wrist", "side"]
    proprio_keys = ["tcp_pose", "tcp_vel", "tcp_force", "tcp_torque", "gripper_pose"]
    buffer_period = 1000
    checkpoint_period = 5000
    steps_per_update = 50
    encoder_type = "resnet-pretrained"
    setup_mode = "single-arm-fixed-gripper"

    def get_environment(self, fake_env=False, save_video=False, classifier=False):
        env = ChargerInsertionEnv(
            fake_env=fake_env,
            save_video=save_video,
            config=EnvConfig(),
        )
        env = GripperCloseEnv(env)
        if not fake_env:
            env = SpacemouseIntervention(env)
        env = RelativeFrame(env)
        env = Quat2EulerWrapper(env)
        env = SERLObsWrapper(env, proprio_keys=self.proprio_keys)
        env = ChunkingWrapper(env, obs_horizon=1, act_exec_horizon=None)
        if classifier:
            classifier = load_classifier_func(
                key=jax.random.PRNGKey(0),
                sample=env.observation_space.sample(),
                image_keys=self.classifier_keys,
                checkpoint_path=os.path.abspath("classifier_ckpt/"),
            )

            def reward_func(obs):
                sigmoid = lambda x: 1 / (1 + jnp.exp(-x))
                # added check for z position to further robustify classifier, but should work without as well
                classifier_output = classifier(obs)
                # 提取标量值：使用.item()或索引[0]来获取标量
                classifier_prob = sigmoid(classifier_output).item() if hasattr(classifier_output, 'item') else sigmoid(classifier_output)[0]
                return int(classifier_prob > 0.85 and obs['state'][0, 6] > 0.04)

            env = MultiCameraBinaryRewardClassifierWrapper(env, reward_func)
        return env