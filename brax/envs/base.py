# Copyright 2023 The Brax Authors.
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

# pylint:disable=g-multiple-import
"""A brax environment for training and inference."""

import abc
from typing import Any, Dict, Optional

from jax.random import KeyArray

from brax import base, System
from brax.generalized import pipeline as g_pipeline
from brax.positional import pipeline as p_pipeline
from brax.spring import pipeline as s_pipeline
from flax import struct
import jax
from jax import numpy as jp

def none_factory():
  return None

@struct.dataclass
class State:
  """Environment state for training and inference."""

  pipeline_state: Optional[base.State]
  obs: jp.ndarray
  reward: jp.ndarray
  done: jp.ndarray
  sys: System
  metrics: Dict[str, jp.ndarray] = struct.field(default_factory=dict)
  info: Dict[str, Any] = struct.field(default_factory=dict)
  vsys_rng: Optional[KeyArray] = None #struct.field(pytree_node=False, default_factory=none_factory)
  vsys_stepcount: Optional[int] = None #struct.field(pytree_node=True, default_factory=none_factory)


class Env(abc.ABC):
  """Interface for driving training and inference."""

  @abc.abstractmethod
  def reset(self, sys: System, rng: jp.ndarray) -> State:
    """Resets the environment to an initial state."""

  @abc.abstractmethod
  def step(self, state: State, action: jp.ndarray) -> State:
    """Run one timestep of the environment's dynamics."""

  @property
  @abc.abstractmethod
  def observation_size(self) -> int:
    """The size of the observation vector returned in step and reset."""

  @property
  @abc.abstractmethod
  def action_size(self) -> int:
    """The size of the action vector expected by step."""

  @property
  @abc.abstractmethod
  def backend(self) -> str:
    """The physics backend that this env was instantiated with."""

  @property
  def unwrapped(self) -> 'Env':
    return self


class PipelineEnv(Env):
  """API for driving a brax system for training and inference."""

  __pytree_ignore__ = (
      '_backend',
      '_pipeline',
  )

  def __init__(
      self,
      sys: base.System,
      backend: str = 'generalized',
      n_frames: int = 1,
      debug: bool = False,
  ):
    """Initializes PipelineEnv.

    Args:
      sys: system defining the kinematic tree and other properties
      backend: string specifying the physics pipeline
      n_frames: the number of times to step the physics pipeline for each
        environment step
      debug: whether to get debug info from the pipeline init/step
    """
    self.sys = sys

    pipeline = {
        'generalized': g_pipeline,
        'spring': s_pipeline,
        'positional': p_pipeline,
    }
    if backend not in pipeline:
      raise ValueError(f'backend should be in {pipeline.keys()}.')

    self._backend = backend
    self._pipeline = pipeline[backend]
    self._n_frames = n_frames
    self._debug = debug

  def pipeline_init(self, sys: System, q: jp.ndarray, qd: jp.ndarray) -> base.State:
    """Initializes the pipeline state."""
    return self._pipeline.init(sys, q, qd, self._debug)

  def pipeline_step(
      self, sys: System, pipeline_state: Any, action: jp.ndarray
  ) -> base.State:
    """Takes a physics step using the physics pipeline."""

    def f(state, _):
      return (
          self._pipeline.step(sys, state, action, self._debug),
          None,
      )

    return jax.lax.scan(f, pipeline_state, (), self._n_frames)[0]

  @property
  def dt(self) -> jp.ndarray:
    """The timestep used for each env step."""
    return self.sys.dt * self._n_frames

  @property
  def observation_size(self) -> int:
    rng = jax.random.PRNGKey(0)
    reset_state = self.unwrapped.reset(self.sys, rng)
    return reset_state.obs.shape[-1]

  @property
  def action_size(self) -> int:
    return self.sys.act_size()

  @property
  def backend(self) -> str:
    return self._backend


class Wrapper(Env):
  """Wraps an environment to allow modular transformations."""

  def __init__(self, env: Env):
    self.env = env

  def reset(self, sys: System, rng: jp.ndarray) -> State:
    return self.env.reset(sys, rng)

  def step(self, state: State, action: jp.ndarray) -> State:
    return self.env.step(state, action)

  @property
  def observation_size(self) -> int:
    return self.env.observation_size

  @property
  def action_size(self) -> int:
    return self.env.action_size

  @property
  def unwrapped(self) -> Env:
    return self.env.unwrapped

  @property
  def backend(self) -> str:
    return self.unwrapped.backend

  def __getattr__(self, name):
    if name == '__setstate__':
      raise AttributeError(name)
    return getattr(self.env, name)
