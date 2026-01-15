# Franka机械臂训练指南

我们演示了如何使用HIL-SERL与真实机器人机械臂完成论文中展示的4个任务：RAM插入、USB拾取与插入、物体交接和鸡蛋翻转。这些代表性任务被选择来突出我们的代码库支持的各种使用场景，例如双臂支持（物体交接）、多阶段奖励任务（USB拾取与插入）和动态任务（鸡蛋翻转）。我们为RAM插入任务提供了完整的训练和评估流程的详细说明和技巧，因此建议您仔细阅读此部分作为入门。

## 1. RAM插入

### 操作流程

#### 机器人设置
如果您尚未完成，请先阅读[README.md](../README.md)中关于设置Python环境和安装Franka控制器的说明。以下步骤假设所有安装步骤已完成且Python环境已激活。要设置工作空间，您可以参考我们论文中的工作空间设置图片。

1. 通过编辑`Desk > Settings > End-effector > Mechanical Data > Mass`来调整腕部摄像头的重量。

2. 解锁机器人并在Franka Desk中激活FCI。`franka_server`启动文件位于[serl_robot_infra/robot_servers/launch_right_server.sh](../serl_robot_infra/robot_servers/launch_right_server.sh)。您需要编辑`setup.bash`路径以及`python franka_server.py`命令的标志。您可以参考[serl_robot_infra的README.md](../serl_robot_infra/README.md)来了解如何设置这些标志。要启动服务器，请运行：
   
```bash
bash serl_robot_infra/robot_servers/launch_right_server.sh
```

#### 编辑训练配置
对于每个任务，我们在experiments文件夹中创建一个文件夹来存储数据（即任务演示、奖励分类器数据、训练运行检查点）、启动脚本和训练配置（参见[experiments/ram_insertion](../examples/experiments/ram_insertion/)）。接下来，我们将逐步介绍您需要在[experiments/ram_insertion/config.py](../examples/experiments/ram_insertion/config.py))中进行的所有更改以开始训练：

3. 首先，在`EnvConfig`类中，将`SERVER_URL`更改为运行中的Franka服务器的URL。

4. 接下来，我们需要配置摄像头。对于此任务，我们使用了两个腕部摄像头。任务中使用的所有摄像头（包括奖励分类器和策略训练）都列在`EnvConfig`类的`REALSENSE_CAMERAS`中，它们对应的图像裁剪设置在`IMAGE_CROP`中。用于策略训练和奖励分类器的摄像头键分别列在`TrainConfig`类的`image_keys`和`classifier_keys`中。将`REALSENSE_CAMERAS`中的序列号更改为您设置中摄像头的序列号（这可以在RealSense Viewer应用程序中找到）。要调整图像裁剪（可能还有曝光），您可以运行奖励分类器数据收集脚本（参见步骤6）或演示数据收集脚本（参见步骤8）来可视化摄像头输入。

5. 最后，我们需要为训练过程收集一些位姿。对于此任务，`TARGET_POSE`指的是将RAM条完全插入主板时的臂部位姿，`GRASP_POSE`指的是抓取放置在支架上的RAM条时的臂部位姿，`RESET_POSE`指的是重置时的臂部位姿。`ABS_POSE_LIMIT_HIGH`和`ABS_POSE_LIMIT_LOW`决定了策略的边界框。我们启用了`RANDOM_RESET`，意味着每次重置时都会在`RESET_POSE`周围进行随机化（`RANDOM_XY_RANGE`和`RANDOM_RZ_RANGE`控制随机化程度）。您应该重新收集`TARGET_POSE`、`GRASP_POSE`，并确保边界框设置为安全探索。要收集Franka臂的当前位置，您可以运行：
    ```bash
    curl -X POST http://<FRANKA_SERVER_URL>:5000/getpos_euler
    ```

#### 训练奖励分类器
此任务的奖励通过基于摄像头图像训练的奖励分类器给出。对于此任务，我们使用与策略训练相同的两个腕部图像来训练奖励分类器。以下步骤介绍了收集分类器数据和训练奖励分类器的过程。

> **提示**：根据判断是否应给予任务奖励的难度，有时为分类器使用单独的摄像头或同一摄像头图像的多个缩放裁剪可能是有益的。

6. 首先，我们需要收集分类器的训练数据。导航到examples文件夹并运行：
    ```bash
    cd examples
    python record_success_fail.py --exp_name charger_insertion --successes_needed 200
    ```
   脚本运行时，所有记录的转换默认标记为负（或无奖励）。如果在转换期间按住空格键，则该转换将被标记为正。当收集到足够的正转换时，脚本将终止（默认为200，但可以通过successes_needed标志设置）。对于此任务，您应该收集RAM条在工作空间中各种位置和插入过程中的负转换，并在RAM完全插入时按下空格键。分类器数据将保存到`experiments/ram_insertion/classifier_data`文件夹。

   > **提示**：为了训练一个对假阳性具有鲁棒性的分类器（这对于训练成功的策略很重要），我们发现收集2-3倍于正转换的负转换以覆盖所有故障模式是有帮助的。例如，对于RAM插入，这可能包括尝试在主板上的错误位置插入、仅插入一半，或将RAM条紧挨着插槽持有。

7. 要训练奖励分类器，导航到此任务的实验文件夹并运行：
    ```bash
    cd experiments/ram_insertion
    python ../../train_reward_classifier.py --exp_name charger_insertion
    ```
   奖励分类器将在训练配置中指定的分类器键对应的摄像头图像上进行训练。训练好的分类器将保存到`experiments/charger_insertion/classifier_ckpt`文件夹。

#### 记录演示
少量的人类演示对于加速强化学习过程至关重要，对于此任务，我们使用20个演示。

8. 要使用spacemouse记录20个演示，请运行：
    ```bash
    python ../../record_demos.py --exp_name ram_insertion --successes_needed 20
    ```
   一旦情节被奖励分类器判定为成功或情节超时，机器人将重置。脚本将在收集到20个成功演示后终止，这些演示将保存到`experiments/ram_insertion/demo_data`文件夹。

     > **提示**：在演示数据收集过程中，您可能会注意到奖励分类器输出假阳性（情节终止时给予奖励但没有成功插入）或假阴性（尽管成功插入但没有给予奖励）。在这种情况下，您应该收集额外的分类器数据以针对观察到的分类器故障模式（例如，如果分类器对在空中持有RAM条给出假阳性，您应该收集更多该情况的负数据）。或者，您也可以调整奖励分类器阈值，尽管我们强烈建议在这样做之前收集额外的分类器数据（或者如果需要，添加更多分类器摄像头/图像）。

#### 策略训练
策略训练通过actor节点和learner节点异步完成，actor节点负责在环境中执行策略并将收集的转换发送给learner，learner节点负责训练策略并将更新后的策略发送回actor。在策略训练期间，actor和learner都应运行。

9. 在RAM插入实验对应的文件夹（[experiments/ram_insertion](../examples/experiments/ram_insertion/)）中，您将找到`run_actor.sh`和`run_learner.sh`。在两个脚本中，编辑`checkpoint_path`指向训练过程中生成的检查点和其他数据将保存到的文件夹，在`run_learner.sh`中，编辑`demo_path`指向记录的演示的路径（如果有多个演示文件，您可以提供多个`demo_path`标志）。要开始训练，启动两个节点：
    ```bash
    bash run_actor.sh
    bash run_learner.sh
    ```

    > **提示**：要恢复先前的训练运行，只需将`checkpoint_path`编辑为指向先前运行对应的文件夹，代码将自动加载最新的检查点和训练缓冲区数据并恢复训练。

10. 在训练期间，您应该根据需要给予一些spacemouse干预以加速训练运行，特别是在运行开始阶段或当策略反复探索不正确行为时（例如将RAM条移离主板）。作为参考，在启用随机化和偶尔干预的情况下，策略大约需要1.5小时收敛到100%成功率。

    > **提示**：对于此任务，我们在抓取位姿中添加了一些进一步的随机化。因此，您应该定期重新抓取RAM条，按下F1并将RAM放回支架。

11. 要评估训练好的策略，将标志`--eval_checkpoint_step=CHECKPOINT_NUMBER_TO_EVAL`和`--eval_n_trajs=N_TIMES_TO_EVAL`添加到`run_actor.sh`。然后启动actor：
    ```bash
    bash run_actor.sh
    ```

## 2. USB拾取与插入

### 操作流程

#### 机器人设置
这些步骤假设您已完成所有安装程序且Python环境已激活。要设置工作空间，您可以参考我们论文中的工作空间设置图片。

1. 通过编辑`Desk > Settings > End-effector > Mechanical Data > Mass`来调整腕部摄像头的重量。

2. 解锁机器人并在Franka Desk中激活FCI。如果您尚未完成，您需要编辑`franka_server`启动文件（参考RAM插入说明中的步骤2）。要启动服务器，请运行：
   
```bash
bash serl_robot_infra/robot_servers/launch_right_server.sh
```

#### 编辑训练配置
接下来，我们需要编辑[experiments/usb_pickup_insertion/config.py](../examples/experiments/usb_pickup_insertion/config.py))中的训练配置以开始训练：

3. 首先，在`EnvConfig`类中，将`SERVER_URL`更改为运行中的Franka服务器的URL。

4. 接下来，我们需要配置摄像头。对于此任务，我们使用了2个腕部摄像头和1个侧面摄像头（策略和分类器使用不同的裁剪）。将`REALSENSE_CAMERAS`中的序列号更改为您设置中摄像头的序列号（这可以在RealSense Viewer应用程序中找到）并调整`IMAGE_CROP`中的图像裁剪。要可视化摄像头视图，您可以运行奖励分类器数据收集脚本或演示数据收集脚本。

> **注意**：此配置是如何使用同一摄像头的多个裁剪视图的示例。对于同一摄像头的每个裁剪视图，您需要向`REALSENSE_CAMERAS`和`IMAGE_CROP`添加一个条目。请注意，我们在[experiments/usb_pickup_insertion/wrapper.py](../examples/experiments/usb_pickup_insertion/wrapper.py))中的`USBEnv`的`init_cameras`函数中避免多次初始化同一摄像头。

5. 最后，您需要收集`TARGET_POSE`，对于此任务，指的是当USB完全插入端口时抓取USB的臂部位姿。同时，确保边界框设置为安全探索（参见`ABS_POSE_LIMIT_HIGH`和`ABS_POSE_LIMIT_LOW`）。请注意，`RESET_POSE`（在情节重置期间放下USB之前移动臂部的位姿）已定义，并且`RANDOM_RESET`已启用。要收集Franka臂的当前位置，您可以运行：
    ```bash
    curl -X POST http://<FRANKA_SERVER_URL>:5000/getpos_euler
    ```

#### 训练奖励分类器
对于此任务，我们使用侧面摄像头的裁剪视图来训练奖励分类器。以下步骤介绍了收集分类器数据和训练奖励分类器的过程。

6. 首先，我们需要收集分类器的训练数据。导航到examples文件夹并运行：
    ```bash
    cd examples
    python record_success_fail.py --exp_name usb_pickup_insertion
    ```
   有关使用此脚本的更多详细信息，请参考RAM插入说明中的步骤6。对于此任务，我们发现收集RAM条在工作场所各种位置的负转换、仅部分成功的插入以及成功插入错误USB端口的情况是有帮助的。分类器数据将保存到`experiments/usb_pickup_insertion/classifier_data`文件夹。

7. 要训练奖励分类器，导航到此任务的实验文件夹并运行：
    ```bash
    cd experiments/usb_pickup_insertion
    python ../../train_reward_classifier.py --exp_name usb_pickup_insertion
    ```
   奖励分类器将在训练配置中指定的分类器键对应的摄像头图像上进行训练。训练好的分类器将保存到`experiments/usb_pickup_insertion/classifier_ckpt`文件夹。

#### 记录演示
少量的人类演示对于加速强化学习过程至关重要，对于此任务，我们使用20个演示。

8. 要使用spacemouse记录20个演示，请运行：
    ```bash
    python ../../record_demos.py --exp_name usb_pickup_insertion --successes_needed 20
    ```
   一旦情节被奖励分类器判定为成功或情节超时，机器人将重置。这也是验证奖励分类器和重置是否按预期工作的好机会。脚本将在收集到20个成功演示后终止，这些演示将保存到`experiments/usb_pickup_insertion/demo_data`文件夹。

#### 策略训练

9. 在USB拾取和插入实验对应的文件夹（[experiments/usb_pickup_insertion](../examples/experiments/usb_pickup_insertion/)）中，您将找到`run_actor.sh`和`run_learner.sh`。在两个脚本中，编辑`checkpoint_path`指向训练过程中生成的检查点和其他数据将保存到的文件夹，在`run_learner.sh`中，编辑`demo_path`指向记录的演示的路径（如果有多个演示文件，您可以提供多个`demo_path`标志）。要开始训练，启动两个节点：
    ```bash
    bash run_actor.sh
    bash run_learner.sh
    ```

10. 在训练期间，您应该根据需要给予一些spacemouse干预以加速训练运行，特别是在运行开始阶段或当策略反复探索不正确行为时（例如将USB移离主板）。作为参考，我们的策略大约需要2.5小时收敛到100%成功率。

11. 要评估训练好的策略，将标志`--eval_checkpoint_step=CHECKPOINT_NUMBER_TO_EVAL`和`--eval_n_trajs=N_TIMES_TO_EVAL`添加到`run_actor.sh`。然后启动actor：
    ```bash
    bash run_actor.sh
    ```

## 3. 物体交接
说明即将推出！

## 4. 鸡蛋翻转
说明即将推出！

## 成功附加技巧
- 给予人类干预的技巧
    - 首先，使用spacemouse进行干预（像键盘这样的东西精度要低得多）！
    - 在训练的开始阶段频繁给予干预（这可以是每个情节或每隔一个情节干预一些时间步）。在让策略探索（对RL至关重要）和通过干预引导其高效探索之间取得平衡很重要。例如，对于插入任务（如RAM插入），在训练开始时，策略会有很多随机运动。我们通常会让它探索这些随机运动20-30个时间步，然后干预以引导物体靠近插入端口，在那里让策略练习插入。在探索和干预之间交替将为策略提供探索任务每个部分的机会，同时不会浪费时间探索完全错误的行为（例如在远离插入端点的边界框边缘探索随机运动）。我们还发现，在开始时半频繁地干预以帮助策略完成任务并获得奖励是有益的（即让1/3或更多的情节获得奖励）- 频繁的奖励将有助于价值备份传播更快并加速训练。
    - 当策略开始表现得更合理时（策略可以自己成功完成任务，偶尔需要最少/不需要干预），我们可以显著减少干预频率。在这个阶段，我们大多会停止干预，除非策略反复犯同样的错误。
    - 有时，我们可能希望训练好的策略具有更鲁棒的重试行为（意味着策略即使在早期犯错也能成功完成任务）或对外部干扰更鲁棒。在这种情况下，我们也可以使用干预来帮助它练习这些边缘情况。例如，如果我们希望我们的USB拾取和插入策略对边缘情况具有鲁棒性（例如，在首次尝试失败后将USB掉落在主板附近后仍能成功插入USB），我们可以干预使策略犯这个错误，并让它练习从中恢复。使用干预将策略带到练习这些恢复行为的地方对于达到100%成功率是有效的，因为这些错误可能发生得太少，但策略仍然需要学习如何恢复以从97%成功率的策略改进到100%成功率的策略。

更多内容即将推出！