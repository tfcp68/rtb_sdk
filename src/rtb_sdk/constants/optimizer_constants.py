from rtb_sdk.schemas import OptimizationMethodId, OptimizationStrategyId, DiscriminatedOptimizerType


class OptimizationMethod:
    GRID_SEARCH: OptimizationMethodId = "grid"
    GENETIC_SEARCH: OptimizationMethodId = "genetic"

class OptimizationStrategies:
    MAXIMIZE: OptimizationStrategyId = "maximize"
    MINIMIZE: OptimizationStrategyId = "minimize"
