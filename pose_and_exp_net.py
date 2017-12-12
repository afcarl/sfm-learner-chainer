# Original implementation with TF : https://github.com/tinghuiz/SfMLearner/blob/master/nets.py
import chainer
from chainer import functions as F
from chainer import links as L


class PoseAndExpNet(chainer.Chain):
    def __init__(self, n_source=2, activtion=F.relu):
        super(PoseAndExpNet, self, ).__init__()
        self.activation = activtion
        self.n_source = n_source
        with self.init_scope():
            self.c1 = L.Convolution2D(None, 16, ksize=8, stride=2, pad=3)
            self.c2 = L.Convolution2D(None, 32, ksize=6, stride=2, pad=2)
            self.c3 = L.Convolution2D(None, 64, ksize=4, stride=2, pad=1)
            self.c4 = L.Convolution2D(None, 128, ksize=4, stride=2, pad=1)
            self.c5 = L.Convolution2D(None, 256, ksize=4, stride=2, pad=1)

            self.pose1 = L.Convolution2D(None, 256, ksize=4, stride=2, pad=1)
            self.pose2 = L.Convolution2D(None, 256, ksize=4, stride=2, pad=1)
            self.poseout = L.Convolution2D(None, n_source * 2, ksize=1, stride=0, pad=0)

            self.exp5 = L.Deconvolution2D(None, 256, ksize=4, stride=2, pad=1)
            self.exp4 = L.Deconvolution2D(None, 128, ksize=4, stride=2, pad=1)
            self.expout4 = L.Deconvolution2D(None, n_source * 2, ksize=4, stride=2, pad=1)
            self.exp3 = L.Deconvolution2D(None, 64, ksize=4, stride=2, pad=1)
            self.expout3 = L.Deconvolution2D(None, n_source * 2, ksize=4, stride=2, pad=1)
            self.exp2 = L.Deconvolution2D(None, 32, ksize=6, stride=2, pad=2)
            self.expout2 = L.Deconvolution2D(None, n_source * 2, ksize=6, stride=2, pad=2)
            self.exp1 = L.Deconvolution2D(None, 32, ksize=6, stride=2, pad=2)
            self.expout1 = L.Deconvolution2D(None, n_source * 2, ksize=8, stride=2, pad=3)

    def encode(self, x):
        normalizer = lambda z: z
        h = x
        h = self.activation(normalizer(self.c1(h)))
        h = self.activation(normalizer(self.c2(h)))
        h = self.activation(normalizer(self.c3(h)))
        h = self.activation(normalizer(self.c4(h)))
        h = self.activation(normalizer(self.c5(h)))
        return h

    def pose(self, x):
        normalizer = lambda z: z
        h = x
        h = self.activation(normalizer(self.pose1(h)))
        h = self.activation(normalizer(self.pose2(h)))
        h = self.poseout(h)
        # Empirically the authors found that scaling by a small constant
        # facilitates training.
        h = 0.01 * F.mean(h, (2, 3))
        h = F.split_axis(h, self.n_source, 1)
        return h

    def exp(self, x):
        normalizer = lambda z: z
        h = x
        h = self.activation(normalizer(self.exp5(h)))
        h = self.activation(normalizer(self.exp4(h)))
        mask4 = self.expout4(h)
        h = self.activation(normalizer(self.exp3(h)))
        mask3 = self.expout3(h)
        h = self.activation(normalizer(self.exp2(h)))
        mask2 = self.expout2(h)
        h = self.activation(normalizer(self.exp1(h)))
        mask1 = self.expout1(h)
        return [mask1, mask2, mask3, mask4]

    def __call__(self, x_target, x_sources, do_exp=True):
        """
        x_target: chainer.Variable of shape [N, 3, H, W]
        x_sources: list. len(list)=self. n_source. list[i] should be chainer.Variable of shape [N, 3, H_i, W_i]
        """
        if len(x_sources) != self.n_source:
            raise Exception("len(x_sources) should match to self.n_source")
        h = F.concat([x_target, F.concat(x_sources, axis=1)], axis=1)
        h = self.encode(h)
        poses = self.pose(h)
        if do_exp:
            return poses
        else:
            masks = self.exp(h)
            return poses, masks
