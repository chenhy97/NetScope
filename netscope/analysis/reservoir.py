import numpy as np


class Reservoir():

    def __init__(self, sigma_num=3, volumn=1e3):
        self.k = volumn  # size of reservoir
        self.decay_rate = 0.8

        self.R = []  # reservoir
        self.R_sub = []
        self.c_w = 0  # current weight
        self.batch_count = 0  # batch size counter for batch-based decay
        self._decay_threshold = self.k / self.decay_rate  # batch-based decay threshold
        self.sigma_num = sigma_num
        # print(f"error bar: {sigma_num} sigma")

        self.abnormal_counter = 0  # continuous abnormal counter

    def observe(self, point, weight=1):
        self.decay()

        self.c_w += weight
        self.batch_count += 1

        prob = 0.8
        # punish = 1
        # prob = self.k / (self.c_w + 1)  # with probability k/c_w
        punish = np.exp(self.abnormal_counter)  # punish if continuous abnormal

        if np.random.rand() < prob / punish:
            self.R.pop(np.random.randint(0, len(self.R)))
            self.R.append(point)
        # else:
        #     self.c_w += weight
        #     self.batch_count += 1

    def decay(self):
        if self.batch_count > self._decay_threshold:
            self.c_w *= self.decay_rate
            self.batch_count = 0

    def threshold(self):
        return
        # return max(self.R)
        median = np.median(self.R)
        distance = abs(np.array(self.R) - median)
        d_m = np.median(distance)  # median of absolute distance
        d_p = np.percentile(distance, 90)
        print(self.R)
        print(list(distance))
        print(median, d_p)
        threshold = median + d_p
        threshold *= self.sigma_num
        return threshold

    def judge(self, point):
        layback = 0.99
        self.R_sub = self.R[:int(self.k * layback)]
        result = np.abs(point - np.median(self.R_sub)) > np.std(
            self.R_sub) * self.sigma_num

        # result = point > self.threshold()

        if result:
            self.abnormal_counter += 1
        else:
            self.abnormal_counter = 0
        return result

    def feed(self, point):
        if len(self.R) < self.k:  # init case
            self.R.append(point)
            return "unknow"
        else:
            judge = self.judge(point)
            self.observe(point, weight=1)
            if judge:
                return "out"
            else:
                return "in"
