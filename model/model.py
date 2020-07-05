"""
Class defintion for q learning agent and policy gradient agent
"""
import torch
import torch.nn as nn
import numpy as np
from torch.distributions import Categorical
from model.replay_buffer import ReplayBuffer, ReplayBufferMulti
import cv2
import logging

class DQNAgent(nn.Module):
    def __init__(self, state_space, action_space, eps=0.99, lr=1e-3, buf_len=1000, gamma=0.99, decay=0.99):
        super(DQNAgent, self).__init__()

        self.state_space = state_space
        self.action_space = action_space
        self.eps = eps
        self.lr = lr
        self.replay_memory = ReplayBuffer(buf_len=buf_len)

        self.lin1 = nn.Linear(state_space, 512)
        self.lin1_ = nn.Linear(512, 256)
        self.lin2 = nn.Linear(256, action_space)
        self.gamma = gamma
        self.decay = decay

    def store_experience(self, experience):
        """

        Store experience tuple in replay buffer
        """

        self.replay_memory.store_experience(experience)

    def forward(self, x):
        """

        Forward pass of DQN
        """

        x = torch.relu(self.lin1(x))
        x = torch.relu(self.lin1_(x))
        x = self.lin2(x)

        return x


    def choose_action(self, state):
        """

        Select action according to q value or random
        """
        action = None

        if (self.eps > np.random.rand()): # Select random action if eps happened
            action = np.random.randint(self.action_space)

            #print ("selecting random action")

        else: # Get q_value with highest action
            q_values = self.forward(state)
            action = torch.argmax(q_values).item()

            #print ("selecting greedy action")


        return action


    def anneal_eps(self):
        if (self.eps > 0.1):
            self.eps *= self.decay
        

class PGAgent(nn.Module):
    """

    Class implementation for policy gradient
    """

    def __init__(self, state_space, action_space, hidden_dim=128):
        super(PGAgent, self).__init__()

        self.state_space = state_space
        self.action_space = action_space

        # Policy network
        self.lin1 = nn.Linear(state_space, hidden_dim)
        self.lin2 = nn.Linear(hidden_dim, action_space)

        # Storage for trajectory rollout
        self.rewards = []
        self.log_probs = []

    def forward(self, x):
        """

        Forward pass for policy network
        """
        x = torch.relu(self.lin1(x))
        x = self.lin2(x)

        probs = torch.softmax(x, dim=0)

        return probs


    def select_action(self, state):
        """

        Probablistically select action according to policy
        """
        probs = self.forward(state)
        dist = Categorical(probs)
        action = dist.sample()

        log_prob_tensor = torch.log(dist.probs[action])
        #log_prob_tensor.requires_grad = True

        self.log_probs.append(log_prob_tensor)

        return action

    def flush_buffers(self):
        self.rewards = []
        self.log_probs = []


class DQNConvAgent(nn.Module):
    def __init__(self, state_space, action_space, eps=0.99, lr=1e-3, buf_len=1000, gamma=0.7, decay=0.99):
        super(DQNConvAgent, self).__init__()

        self.state_space = state_space
        self.action_space = action_space
        self.eps = eps
        self.lr = lr
        self.replay_memory = ReplayBufferMulti(state_size=state_space, buf_len=buf_len)

        # self.conv1 = nn.Conv2d(1, 32, 3, 2)
        # self.conv2 = nn.Conv2d(32, 64, 3, 2)
        # self.conv3 = nn.Conv2d(64, 64, 3, 2)
        # self.conv4 = nn.Conv2d(64, 64, 3, 2)
        c_out = 4
        kernel = 5
        stride = 1
        c_in, h_in, w_in = state_space
        self.conv1 = nn.Conv2d(in_channels=c_in, out_channels=c_out, kernel_size=kernel, stride=stride)
        h_out = int((h_in + 2*0 - 1 * (kernel-1) - 1) / stride + 1)
        w_out = int((w_in + 2*0 - 1 * (kernel-1) - 1) / stride + 1)
        logging.debug(f"h_in: {h_in}, w_in: {w_in}")
        logging.debug(f"h_out: {h_out}, w_out: {w_out}")
        self.conv_out = int(h_out * w_out * c_out)
        self.linear_in = self.conv_out + w_in
        # self.lin1 = nn.Linear(7744, 512)
        # self.lin1_ = nn.Linear(512, 256)
        # self.lin2 = nn.Linear(256, action_space)
        logging.debug(f"action_space: {action_space}")
        logging.debug(f"self.conv_out: {self.conv_out}")
        logging.debug(f"self.linear_in: {self.linear_in}")
        self.lin1 = nn.Linear(in_features=self.linear_in, out_features=action_space)
        self.gamma = gamma
        self.decay = decay

    def store_experience(self, experience):
        """

        Store experience tuple in replay buffer
        """

        self.replay_memory.store_experience(experience)

    def forward(self, x):
        """

        Forward pass of DQN
        """
        top_row = x[:, :, 0, :]
        # logging.debug(f"top_row: {top_row}")
        x = torch.relu(self.conv1(x))
        x = x.view(x.shape[0], -1)
        top_row = top_row.view(top_row.shape[0], -1)
        x = torch.cat((x, top_row), dim=1)

        # x = torch.relu(self.conv2(x))
        # x = torch.relu(self.conv3(x))
        #x = torch.relu(self.conv4(x))

        #view = x[0][0].view(14, 15, 1)
        #view = view.cpu().detach().numpy()

        #cv2.imshow("conv", view)
        #cv2.waitKey(1)

        # x = x.view(-1, self.conv_out)
        # logging.debug(f"x before lin1: {x}")
        # logging.debug(f"x.shape: {x.shape}")
        x = self.lin1(x)
        # logging.debug(f"x after lin1: {x}")
        # x = torch.relu(self.lin1_(x))
        # x = self.lin2(x)

        return x

    def choose_action(self, state):
        """

        Select single action according to q value or random
        """
        action = None

        if (self.eps > np.random.rand()): # Select random action if eps happened
            # logging.debug(f"self.action_space: {self.action_space}")
            action = np.random.randint(self.action_space)

        else:  # Get q_value with highest action
            q_values = self.forward(state.unsqueeze(0))
            # logging.debug(f"q_values: {q_values}")
            action = torch.argmax(q_values).item()

        # logging.debug(f"action: {action}")

        return action

    def anneal_eps(self):
        if self.eps > 0.1:
            self.eps *= self.decay