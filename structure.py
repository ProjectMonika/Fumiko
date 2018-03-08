import numpy as np
from pprint import pprint


def sigmoid(z):
    return 1.0/(1.0+np.exp(-z))


def sigmoid_prime(z):
    return sigmoid(z)*(1-sigmoid(z))


class Cost:
    @staticmethod
    def calc(neuron: np.array, expected: np.array) -> np.array:
        raise NotImplementedError

    @staticmethod
    def derative(neuron: np.array, expected: np.array) -> np.array:
        raise NotImplementedError


class QuadraticCost(Cost):
    @staticmethod
    def calc(neuron: np.array, expected: np.array) -> np.array:
        return np.square(neuron - expected)

    @staticmethod
    def derative(neuron: np.array, expected: np.array) -> np.array:
        return 2 * (neuron - expected)


class ECost(Cost):
    @staticmethod
    def calc(neuron: np.array, expected: np.array) -> np.array:
        return np.square(np.e**neuron - np.e**expected)


class Neuron:
    def __init__(self, index: int, is_input: bool = False, parents: list = None, char: str = None):
        if not is_input:
            self.parents = parents
            self.weights = np.random.random(len(parents))
            self.bias = np.random.random()

        self.is_input = is_input
        self.value = 0.0
        self.index = index
        self.char = char

    def __mul__(self, other):
        return self.value * other

    @property
    def wxb(self) -> float:
        return np.sum(self.parents * self.weights) + self.bias

    def update_value(self) -> None:
        self.value = float(sigmoid(self.wxb))

    @property
    def name(self):
        return f"{self.char}{self.index}"


class NeuronLayer:
    def __init__(self, index: int, neuron_count: int,
                 parent=None,
                 cost: Cost = QuadraticCost):
        char = chr(65+index)
        if index == 0:
            self.neurons = [Neuron(_, True, char=char) for _ in range(neuron_count)]

        else:
            self.neurons = [Neuron(_, parents=parent.neurons, char=char) for _ in range(neuron_count)]

        self.parent = parent
        self.is_input = (index == 0)
        self.index = index
        self._cost = cost

    def cost(self, expected: np.array) -> float:
        return float(np.sum(self._cost.calc(np.array([neuron.value for neuron in self.neurons]), expected)))

    def input(self, input_data: np.array) -> None:
        if not self.is_input:
            raise TypeError("Layer is not an input layer!")
        for neuron, value in zip(self.neurons, input_data):
            neuron.value = value

    def update(self) -> None:
        for neuron in self.neurons:
            neuron.update_value()

    def visualize(self, graph):
        for neuron in self.neurons:
            graph.node(f"{neuron.name} = {round(float(neuron.value), 2)}", shape='circle', style="filled",
                       fillcolor="#"+3*f"{int(round(float(neuron.value*255))):0>2x}")

    def update_weight_bias(self, weight: np.array, bias: np.array) -> None:
        for neuron, new_data, bias_ in zip(self.neurons, weight, bias):
            neuron.weights += np.array(new_data)
            neuron.bias += float(bias_)
            print(f"DEBUG: {neuron.name} Updated!")


class LayerNetwork:
    def __init__(self, size: list, cost: Cost = QuadraticCost):
        self.cost = cost

        self.size = size

        layer = None
        layers = []
        for index, layer_size in enumerate(size):
            layer = NeuronLayer(index, layer_size, parent=layer, cost=cost)
            layers.append(layer)

        self.layers = layers

    def input(self, data: np.array) -> None:
        self.layers[0].input(data)
        for layer in self.layers[1:]:
            print(f"DEBUG: Layer {layer.index} is updating values...")
            layer.update()

    def save(self, fn) -> None:
        import pickle

        with open(fn, "wb") as f:
            pickle.dump(self, f)

    def load(self, fn) -> None:
        import pickle

        with open(fn, "rb") as f:
            pickle.load(f)

    def get_output(self) -> np.array:
        return np.array([neuron.value for neuron in self.layers[-1].neurons])

    def get_cost(self, expected: np.array) -> float:
        return self.layers[-1].cost(expected)

    def get_gradient(self, output: np.array, a: float = 0.000001) -> list:
        weight_updates = []
        errors = []
        for layer in self.layers[:0:-1]:
            neurons = []
            weight_neurons = []
            for neuron in layer.neurons:
                err = []
                weights = []
                for prev_neuron in layer.parent.neurons:
                    if layer == self.layers[-1]:
                        # d_N = f'(x) * (yN - t)
                        d_n = sigmoid_prime(prev_neuron.value) * self.cost.derative(neuron.value, output[neuron.index])

                        errors.append(float(d_n))
                        weights.append(-a * float(d_n))
                    else:
                        # d_n = f'(x) * d_n+1 * w_n
                        next_layer = errors[len(self.layers) - layer.index - 2]
                        next_layer_neuron_weight = np.sum([next_neuron[neuron.index]
                                                           for next_neuron in next_layer])
                        d_n = (sigmoid_prime(prev_neuron.value) *
                               next_layer_neuron_weight *
                               neuron.weights[prev_neuron.index])

                        errors.append(float(d_n))
                        weights.append(float(-a * next_layer_neuron_weight * neuron.value))

                weight_neurons.append(weights)

            errors.append(neurons)
            weight_updates.append(weight_neurons)

        bias_updates = []
        for layer in self.layers[:0:-1]:
            neurons = []
            for neuron in layer.neurons:
                """
                if layer == self.layers[-1]:
                    # d_N = f'(x) * (yN - t)
                    d_n = sigmoid_prime(prev_neuron.value) * (neuron.value - output[neuron.index])

                    neurons.append(-a * float(d_n))
                else:
                    # d_n = f'(x) * d_n+1 * b_n
                    next_layer = bias_updates[len(self.layers) - layer.index - 2]
                    inv_a = -1 / a
                    next_layer_neuron_weight = np.sum(
                        inv_a * next_neuron for next_neuron in next_layer)
                    d_n = (sigmoid_prime(prev_neuron.value) *
                           next_layer_neuron_weight *
                           neuron.bias)
                    neurons.append(-a * float(d_n))
                """
                neurons.append(0.0)

            bias_updates.append(neurons)

        return weight_updates, bias_updates

    def visualize(self, fn: str = None, label: str = None) -> None:
        import itertools
        import graphviz

        graph = graphviz.Digraph(format="png")
        graph.attr(rankdir="LR", ranksep="4", label=label)

        for layer in self.layers:
            layer.visualize(graph)

        for old, new in zip(self.layers[:-1], self.layers[1:]):
            for old_, new_ in itertools.product(old.neurons, new.neurons):
                graph.edge(f"{old_.name} = {round(float(old_.value), 2)}",
                           f"{new_.name} = {round(float(new_.value), 2)}",
                           label=str(new_.weights[old.index]))

        if fn is None:
            graph.view()
        else:
            graph.render(fn)

    def feed(self, data: np.array, expected: np.array = None) -> np.array:
        self.input(data)
        out = self.get_output()

        if expected is not None:
            self.backprop(expected)

        return out

    def backprop(self, expected: np.array):
            print(f"INFO: Cost: {self.get_cost(expected)}")
            grad, bias = self.get_gradient(expected)
            for weight, bias_, layer in zip(grad[::-1], bias[::-1], self.layers[1:]):
                layer.update_weight_bias(weight, bias_)

    def get_response(self, data: np.array) -> tuple:
        out = self.feed(data)
        pos = np.argmax(out)
        acc = out[pos]
        return pos, float(acc)


def main():
    net = LayerNetwork([784, 16, 16, 10])

    import json
    with open("mnist.json") as f:
        train_data = json.load(f)

    print(train_data[0])

    for i, data in enumerate(train_data[:1000]):
        data['data'] = np.array(data['data']) / 255
        res = np.array([0.0]*10)
        res[int(data['label'])] = 1.0
        net.feed(data['data'], res)

        # net.save("mnist.nn")
        # net.visualize(fn=f"iters/iteration_{i}.gv", label=data['label'])
        # print("done rendering")

    costs = []

    for i, data in enumerate(train_data[:50]):
        data['data'] = np.array(data['data']) / 255
        res = np.array([0.0]*10)
        res[int(data['label'])] = 1.0
        pos, accuracy = net.get_response(data['data'])
        costs.append(net.get_cost(res))
        print(f"Guess: {pos}\nCertainty: {accuracy}\nCorrect: {data['label']}\n-------------------------------")

    print(f"Final cost: {sum(costs)/len(costs)}")

    print("NET STATE")
    for layer in net.layers:
        print(f"LAYER {layer.index}")
        print([n.value for n in layer.neurons])

    return net


if __name__ == "__main__":
    main()
