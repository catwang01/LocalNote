[toc]


# Pytorch onnx


## 安装

使用 conda 安装的 onnx 是有问题的，尽管教程上面说要用下面的 conda 命令安装，但是实际上这样安装的 onnx 是低版本的，许多功能都不支持。

```
conda install -c conda-forge onnx
```

使用 pip 安装就可以了

```
pip install onnx
```

## torch.onnx.export

![75174f7367a7333b0fbcc187f176c22c.png](evernotecid://8E200321-31A9-427B-BECA-CC44235980BC/appyinxiangcom/22483756/ENResource/p14461)

 

## Tracing vs Scripting

输入的维度只能和  dummy_input 的维度相同。

The ONNX exporter can be both trace-based and script-based exporter.
- trace-based means that it operates by executing your model once, and exporting the operators which were actually run during this run. This means that if your model is dynamic, e.g., changes behavior depending on input data, the export won’t be accurate. **Similarly, a trace is likely to be valid only for a specific input size (which is one reason why we require explicit inputs on tracing.)** We recommend examining the model trace and making sure the traced operators look reasonable. If your model contains control flows like for loops and if conditions, trace-based exporter will unroll the loops and if conditions, exporting a static graph that is exactly the same as this run. If you want to export your model with dynamic control flows, you will need to use the script-based exporter.

- script-based means that the model you are trying to export is a ScriptModule. ScriptModule is the core data structure in TorchScript, and TorchScript is a subset of Python language, that creates serializable and optimizable models from PyTorch code.

## 动态 axis

默认 onnx 只支持和 dummy_input 维度相同的推断


```
import torch
import torch.nn as nn

linear_model = nn.Linear(10, 2)
dummy_input = torch.randn(32, 10)
onnx_model_path = "linear.onnx"
torch.onnx.export(linear_model, dummy_input, onnx_model_path, input_names=['input'], output_names=['output'])


import onnxruntime as ort
import numpy as np

sess = ort.InferenceSession(onnx_model_path)
onnx_output = sess.run(None, {'input': np.random.randn(32, 10).astype(np.float32)}) # valid
onnx_another_output = sess.run(None, {'input': np.random.randn(1, 10).astype(np.float32)}) # Error
```

当输入和 dummy_input 相同维度的输入时，正常运行；而当输入和 dummpy_input 不相同的维度时，报错。

```
onnxruntime.capi.onnxruntime_pybind11_state.InvalidArgument: [ONNXRuntimeError] : 2 : INVALID_ARGUMENT : Got invalid dimensions for input: input for the following indices
index: 0 Got: 1 Expected: 32
Please fix either the inputs or the model.
```

这种情况下，可以使用  `torch.onnx.export` 的 dynamic_axes 参数。

```
import torch
import torch.nn as nn

linear_model = nn.Linear(10, 2)
dummy_input = torch.randn(32, 10)
onnx_model_path = "linear.onnx"
torch.onnx.export(linear_model, dummy_input, onnx_model_path, input_names=['input'], output_names=['output'],
                  dynamic_axes={'input': [0]})

import onnxruntime as ort
import numpy as np

sess = ort.InferenceSession(onnx_model_path)
onnx_output = sess.run(None, {'input': np.random.randn(32, 10).astype(np.float32)})  # valid
onnx_another_output = sess.run(None, {'input': np.random.randn(1, 10).astype(np.float32)})  # valid
``` 

## 获取 input 的 name

```
import onnxruntime
sess = onnxruntime.InferenceSession("cnn-text.onnx")
sess.get_inputs()[0].name
```

## 已知bug

在 max_pool1d 时需要用 int


```
pool_size = int(x4.size(2))
x5 = F.max_pool1d(x4, pool_size).squeeze()
```

否则会报错

```
TypeError: max_pool1d(): argument 'kernel_size' (position 2) must be tuple of 
ints, not Tensor
```

解决方法来自于 [ 3 ]![fdaee785d009719e58bd61d1fe573db6.png](evernotecid://8E200321-31A9-427B-BECA-CC44235980BC/appyinxiangcom/22483756/ENResource/p14460)

## optimize

onnx 的 optimize 方法可以对图进行一些优化。

如果遇到下面的报错，则 export 中添加参数

![fdaee785d009719e58bd61d1fe573db6.png](evernotecid://8E200321-31A9-427B-BECA-CC44235980BC/appyinxiangcom/22483756/ENResource/p14460)
 

![872faf8fb90a745b9b03372d0b1a3d4e.png](evernotecid://8E200321-31A9-427B-BECA-CC44235980BC/appyinxiangcom/22483756/ENResource/p14458)


## 如何输出中间层

将其添加到 output https://github.com/onnx/onnx/issues/2218


## shape_inference

[onnx/shape_inference.ipynb at master · onnx/onnx](https://github.com/onnx/onnx/blob/master/onnx/examples/shape_inference.ipynb)

![d4d7a27fa14b70f084b863c630c2e3b9.png](evernotecid://8E200321-31A9-427B-BECA-CC44235980BC/appyinxiangcom/22483756/ENResource/p14462)

## 如何自定义

```
```

# References

1. [torch.onnx — PyTorch 1.6.0 documentation](https://pytorch.org/docs/stable/onnx.html)

2.  [onnx/PythonAPIOverview.md at master · onnx/onnx](https://github.com/onnx/onnx/blob/master/docs/PythonAPIOverview.md#optimizing-an-onnx-model)

3.   [ONNX converts scalar to Tensor, doesn't works with torch.nn.functional.max_pool1d() · Issue #11296 · pytorch/pytorch](https://github.com/pytorch/pytorch/issues/11296)

 https://www.jianshu.com/p/e2a444853e13
4.  一个 ppt https://microsoft.sharepoint.com/:p:/r/teams/STCARelevane/_layouts/15/Doc.aspx?sourcedoc={FFFB9E1E-B675-4D1C-A80F-17EF3928324D}&file=RankLM%20PyTorch%20Repo.pptx&action=edit&mobileredirect=true&DefaultItemOpen=1
hhhhhhhhhhhaha
