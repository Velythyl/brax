# Copyright 2021 The Brax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ant_push Sweep."""
from brax.experimental.braxlines.experiments import defaults

AGENT_MODULE = 'brax.experimental.composer.train'
CONFIG = [
    dict(
        env_name=['ant_push'],
        seed=list(range(10)),
        desc_edits={
            'components.cap1.reward_fns.goal.scale': [0.2, 1, 0.5],
            'components.cap1.reward_fns.goal.target_goal': 5,
        },
        ppo_params=defaults.get_ppo_params('ant'))
]
