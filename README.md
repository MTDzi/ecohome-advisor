# Introduction
This repo contains the code for the EcoHome Energy Advisor project. The purpose of this README is to give a high-level overview of the implementation and evaluation of the agent. For detailed description of the folder structure and tool I refer the reader to [this file](./project/ecohome/README.md).

# Implementation
## Weather forecast
I added a `weather_and_sun.py` module for generating more realistic weather patterns:
![](./project/ecohome/images/simulated_weather_plots.png)

## Tools
For both `tools.get_weather_forecast` and `tools.get_electricity_prices` I settled on using simulated data.

## Agent
I didn't provide a custom workflow graph in the `agent.Agent` class but relied on the simplified graph provided by the `create_react_agent` function:
![](./project/ecohome/default_react_agent_graph.png)

It's simple, BUT thanks to its simplicity the evaluation strategy and conclusions drawn from it were less tainted by a particular choice of a custom workflow graph.

# Evaluation results
I was curious of two things and I reworked the `03_ruin_and_evaluate.ipynb` to find answers to the following questions:
1. How does the size of the model impact performance (`gpt-4o-mini` vs `gpt-40`)
2. How does the temperature of the text generation algorighm impact performance (temperatures between 0.0 and 0.4)

## Results

First, let's take a look at the different response metrics for the two models across different temperatures:

| Temperature  | gpt-4o response metrics | gpt-40-mini response metrics  |
|---|---|---|
| 0.0 | ![](./project/ecohome/images/t=0.0_gpt-4o_metrics.png) | ![](./project/ecohome/images/t=0.0_gpt-4o-mini_metrics.png) |
| 0.1 | ![](./project/ecohome/images/t=0.1_gpt-4o_metrics.png) | ![](./project/ecohome/images/t=0.1_gpt-4o-mini_metrics.png) |
| 0.3 | ![](./project/ecohome/images/t=0.3_gpt-4o_metrics.png) | ![](./project/ecohome/images/t=0.3_gpt-4o-mini_metrics.png) |
| 0.4 | ![](./project/ecohome/images/t=0.4_gpt-4o_metrics.png) | ![](./project/ecohome/images/t=0.4_gpt-4o-mini_metrics.png) |

I found the above visualizations less informative than temperature progression for each metric individually:
| Response metric | gpt-4o | gpt-4o-mini |
|---|---|---|
| accuracy | ![](./project/ecohome/images/gpt-4o_accuracy-progression.png) | ![](./project/ecohome/images/gpt-4o-mini_accuracy-progression.png) |   
| completeness | ![](./project/ecohome/images/gpt-4o_completeness-progression.png) | ![](./project/ecohome/images/gpt-4o-mini_completeness-progression.png) |   
| relevance | ![](./project/ecohome/images/gpt-4o_relevance-progression.png) | ![](./project/ecohome/images/gpt-4o-mini_relevance-progression.png) |   
| usefulness | ![](./project/ecohome/images/gpt-4o_usefulness-progression.png) | ![](./project/ecohome/images/gpt-4o-mini_usefulness-progression.png) |

and for tool use metrics:
| Tool use metric | gpt-4o | gpt-4o-mini |
|---|---|---|
| tool-appropriateness | ![](./project/ecohome/images/gpt-4o_tool-appropriateness-progression.png) | ![](./project/ecohome/images/gpt-4o-mini_tool-appropriateness-progression.png) |   
| tool-completeness | ![](./project/ecohome/images/gpt-4o_tool-completeness-progression.png) | ![](./project/ecohome/images/gpt-4o-mini_tool-completeness-progression.png) |   

Overall averages of all the above scores is as follows:
| Temperature | gpt-4o | gpt-4o-mini |
|---|---|---|
| 0.0 | 74.44 | 72.72 |
| 0.1 | 72.67 | 72.50 |
| 0.3 | 73.17 | 71.89 |
| 0.4 | 73.83 | 73.44 |

## Conclusions
The bigger model has better performance than the smaller one, but not by a whole lot. The INPUT [pricing](https://platform.openai.com/docs/pricing) for `gpt-4o-mini` is $0.15 and for `gpt-4o` it's $2.50, so the larger model is almost **17 times** more expensive! The results I got DO NOT sustain using the bigger model, at least not for this simple task.

I was surprised to see that the temperature didn't impact any of the model all that much. There is clearly a lot of variance in the averages but no clear trend appears that would be applicable to all metrics and even to any particular metric. I think this is mainly due to the limited number of test cases. Still, despite that, I think it's safe to say that temperature is not a critical parameter for the quality of the results.