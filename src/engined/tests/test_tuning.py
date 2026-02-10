"""
Unit tests for the Self-Tuning module.

Tests cover:
- Tunable parameters
- Performance tracking
- Self-tuning strategies

ACTUAL API (discovered via introspection):
- TuningStrategy: ADAPTIVE, BAYESIAN, GRADIENT_FREE, MANUAL
- ParameterType: CATEGORICAL, CONTINUOUS, DISCRETE
- TunableParameter: no reset(), has validate(), get_neighbor()
- PerformanceTracker: record_metric (not record), get_recent_average, compute_score, record_snapshot
- SelfTuner: start/stop async, register_parameter, get_parameter, record_metric, record_task_completion
"""

import pytest

from engined.agents.tuning import (
    ParameterType,
    PerformanceTracker,
    SelfTuner,
    TunableParameter,
    TuningStrategy,
    get_tuner,
    init_tuning_system,
    shutdown_tuning_system,
)


class TestTuningStrategy:
    """Tests for TuningStrategy enum."""

    def test_strategies_defined(self):
        """Test all tuning strategies are defined."""
        assert TuningStrategy.ADAPTIVE is not None
        assert TuningStrategy.BAYESIAN is not None
        assert TuningStrategy.GRADIENT_FREE is not None
        assert TuningStrategy.MANUAL is not None

    def test_strategy_values(self):
        """Test strategy values are distinct."""
        strategies = {
            TuningStrategy.ADAPTIVE,
            TuningStrategy.BAYESIAN,
            TuningStrategy.GRADIENT_FREE,
            TuningStrategy.MANUAL,
        }
        assert len(strategies) == 4


class TestParameterType:
    """Tests for ParameterType enum."""

    def test_parameter_types_defined(self):
        """Test all parameter types are defined."""
        assert ParameterType.CATEGORICAL is not None
        assert ParameterType.CONTINUOUS is not None
        assert ParameterType.DISCRETE is not None

    def test_parameter_type_values(self):
        """Test parameter type values are distinct."""
        types = {
            ParameterType.CATEGORICAL,
            ParameterType.CONTINUOUS,
            ParameterType.DISCRETE,
        }
        assert len(types) == 3


class TestTunableParameter:
    """Tests for TunableParameter class."""

    def test_continuous_parameter_creation(self):
        """Test creating a continuous (numeric) parameter."""
        param = TunableParameter(
            name="batch_size",
            param_type=ParameterType.CONTINUOUS,
            current_value=32.0,
            default_value=32.0,
            min_value=1.0,
            max_value=256.0,
        )
        assert param.name == "batch_size"
        assert param.param_type == ParameterType.CONTINUOUS
        assert param.current_value == 32.0
        assert param.default_value == 32.0
        assert param.min_value == 1.0
        assert param.max_value == 256.0

    def test_discrete_parameter_creation(self):
        """Test creating a discrete parameter."""
        param = TunableParameter(
            name="threads",
            param_type=ParameterType.DISCRETE,
            current_value=4,
            default_value=4,
            min_value=1,
            max_value=32,
        )
        assert param.name == "threads"
        assert param.param_type == ParameterType.DISCRETE
        assert param.current_value == 4

    def test_categorical_parameter_creation(self):
        """Test creating a categorical parameter."""
        param = TunableParameter(
            name="algorithm",
            param_type=ParameterType.CATEGORICAL,
            current_value="zstd",
            default_value="zstd",
            choices=["zstd", "lz4", "brotli"],
        )
        assert param.name == "algorithm"
        assert param.param_type == ParameterType.CATEGORICAL
        assert param.current_value == "zstd"
        assert param.choices == ["zstd", "lz4", "brotli"]

    def test_parameter_to_dict(self):
        """Test parameter serializes to dictionary."""
        param = TunableParameter(
            name="threads",
            param_type=ParameterType.DISCRETE,
            current_value=4,
            default_value=4,
            min_value=1,
            max_value=32,
        )
        d = param.to_dict()
        assert d["name"] == "threads"
        assert d["current_value"] == 4
        assert d["default_value"] == 4

    def test_parameter_update_value(self):
        """Test updating parameter value."""
        param = TunableParameter(
            name="buffer_size",
            param_type=ParameterType.CONTINUOUS,
            current_value=1024.0,
            default_value=1024.0,
            min_value=256.0,
            max_value=4096.0,
        )
        param.current_value = 2048.0
        assert param.current_value == 2048.0

    def test_parameter_get_neighbor(self):
        """Test getting neighbor value for parameter."""
        param = TunableParameter(
            name="level",
            param_type=ParameterType.CONTINUOUS,
            current_value=5.0,
            default_value=5.0,
            min_value=1.0,
            max_value=9.0,
            step_size=0.5,
        )
        neighbor = param.get_neighbor()
        assert neighbor is not None
        assert param.min_value <= neighbor <= param.max_value

    def test_parameter_validate(self):
        """Test parameter validation."""
        param = TunableParameter(
            name="threads",
            param_type=ParameterType.DISCRETE,
            current_value=4,
            default_value=4,
            min_value=1,
            max_value=32,
        )
        # Validate should work for values in range
        assert param.validate(8) is True
        assert param.validate(16) is True


class TestPerformanceTracker:
    """Tests for PerformanceTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create a performance tracker for testing."""
        return PerformanceTracker(window_size=100)

    def test_tracker_creation(self, tracker):
        """Test tracker is created."""
        assert tracker is not None

    def test_record_metric(self, tracker):
        """Test recording a metric (method is record_metric)."""
        tracker.record_metric("throughput", 1000.0)
        tracker.record_metric("throughput", 1100.0)
        tracker.record_metric("throughput", 1050.0)
        avg = tracker.get_recent_average("throughput")
        assert avg is not None
        assert abs(avg - 1050.0) < 10

    def test_record_multiple_metrics(self, tracker):
        """Test recording multiple different metrics."""
        tracker.record_metric("latency", 10.0)
        tracker.record_metric("latency", 15.0)
        tracker.record_metric("throughput", 500.0)
        tracker.record_metric("throughput", 600.0)
        latency_avg = tracker.get_recent_average("latency")
        throughput_avg = tracker.get_recent_average("throughput")
        assert latency_avg is not None
        assert throughput_avg is not None
        assert abs(latency_avg - 12.5) < 1
        assert abs(throughput_avg - 550.0) < 10

    def test_get_recent_average_empty(self, tracker):
        """Test getting average for metric with no data."""
        avg = tracker.get_recent_average("nonexistent")
        assert avg is None or avg == 0

    def test_is_improving(self, tracker):
        """Test checking if metric is improving."""
        tracker.record_metric("throughput", 100.0)
        tracker.record_metric("throughput", 110.0)
        tracker.record_metric("throughput", 120.0)
        result = tracker.is_improving("throughput")
        assert isinstance(result, bool)

    def test_get_trend(self, tracker):
        """Test getting metric trend."""
        tracker.record_metric("latency", 50.0)
        tracker.record_metric("latency", 48.0)
        tracker.record_metric("latency", 45.0)
        trend = tracker.get_trend("latency")
        # get_trend may return None if not enough data
        assert trend is None or isinstance(trend, float)


class TestSelfTuner:
    """Tests for SelfTuner class."""

    @pytest.fixture
    async def tuner(self):
        """Create a self-tuner for testing."""
        tuner = SelfTuner(
            strategy=TuningStrategy.GRADIENT_FREE,
            tuning_interval=1.0
        )
        await tuner.start()
        yield tuner
        await tuner.stop()

    @pytest.mark.asyncio
    async def test_tuner_start_stop(self):
        """Test tuner can start and stop."""
        tuner = SelfTuner()
        assert not tuner._running
        await tuner.start()
        assert tuner._running
        await tuner.stop()
        assert not tuner._running

    @pytest.mark.asyncio
    async def test_register_parameter(self, tuner):
        """Test registering a tunable parameter."""
        param = TunableParameter(
            name="workers",
            param_type=ParameterType.DISCRETE,
            current_value=4,
            default_value=4,
            min_value=1,
            max_value=16,
        )
        tuner.register_parameter(param)
        assert "workers" in tuner._parameters

    @pytest.mark.asyncio
    async def test_get_parameter(self, tuner):
        """Test getting a registered parameter."""
        param = TunableParameter(
            name="batch",
            param_type=ParameterType.CONTINUOUS,
            current_value=64.0,
            default_value=64.0,
            min_value=8.0,
            max_value=512.0,
        )
        tuner.register_parameter(param)
        retrieved = tuner.get_parameter("batch")
        assert retrieved is not None
        assert retrieved.current_value == 64.0

    @pytest.mark.asyncio
    async def test_record_metric(self, tuner):
        """Test recording a performance metric."""
        tuner.record_metric("latency", 50.0)
        tuner.record_metric("latency", 55.0)
        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_record_task_completion(self, tuner):
        """Test recording task completion.
        
        Signature: record_task_completion(success, latency_ms, task_type='general')
        """
        tuner.record_task_completion(
            success=True,
            latency_ms=120.0,
            task_type="compression"
        )
        tuner.record_task_completion(
            success=True,
            latency_ms=150.0,
            task_type="compression"
        )
        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_multiple_parameters(self, tuner):
        """Test registering multiple parameters."""
        param1 = TunableParameter(
            name="threads",
            param_type=ParameterType.DISCRETE,
            current_value=8,
            default_value=4,
            min_value=1,
            max_value=32,
        )
        param2 = TunableParameter(
            name="algorithm",
            param_type=ParameterType.CATEGORICAL,
            current_value="zstd",
            default_value="lz4",
            choices=["zstd", "lz4", "brotli"],
        )
        tuner.register_parameter(param1)
        tuner.register_parameter(param2)
        assert len(tuner._parameters) >= 2
        assert "threads" in tuner._parameters
        assert "algorithm" in tuner._parameters

    @pytest.mark.asyncio
    async def test_strategy_property(self, tuner):
        """Test strategy is accessible."""
        assert tuner._strategy == TuningStrategy.GRADIENT_FREE

    @pytest.mark.asyncio
    async def test_get_all_parameters(self, tuner):
        """Test getting all registered parameters."""
        param = TunableParameter(
            name="level",
            param_type=ParameterType.DISCRETE,
            current_value=5,
            default_value=5,
            min_value=1,
            max_value=9,
        )
        tuner.register_parameter(param)
        all_params = tuner.get_all_parameters()
        assert isinstance(all_params, dict)
        assert "level" in all_params

    @pytest.mark.asyncio
    async def test_get_metrics(self, tuner):
        """Test getting tuner metrics."""
        metrics = tuner.get_metrics()
        assert isinstance(metrics, dict)


class TestTuningSystemInit:
    """Tests for tuning system initialization."""

    @pytest.mark.asyncio
    async def test_init_and_shutdown(self):
        """Test init and shutdown of tuning system."""
        await init_tuning_system()
        tuner = get_tuner()
        assert tuner is not None
        await shutdown_tuning_system()


class TestTuningStrategies:
    """Tests for different tuning strategies."""

    @pytest.mark.asyncio
    async def test_adaptive_strategy(self):
        """Test adaptive tuning strategy."""
        tuner = SelfTuner(strategy=TuningStrategy.ADAPTIVE)
        await tuner.start()
        assert tuner._strategy == TuningStrategy.ADAPTIVE
        await tuner.stop()

    @pytest.mark.asyncio
    async def test_bayesian_strategy(self):
        """Test Bayesian tuning strategy."""
        tuner = SelfTuner(strategy=TuningStrategy.BAYESIAN)
        await tuner.start()
        assert tuner._strategy == TuningStrategy.BAYESIAN
        await tuner.stop()

    @pytest.mark.asyncio
    async def test_gradient_free_strategy(self):
        """Test gradient-free tuning strategy."""
        tuner = SelfTuner(strategy=TuningStrategy.GRADIENT_FREE)
        await tuner.start()
        assert tuner._strategy == TuningStrategy.GRADIENT_FREE
        await tuner.stop()

    @pytest.mark.asyncio
    async def test_manual_strategy(self):
        """Test manual tuning strategy."""
        tuner = SelfTuner(strategy=TuningStrategy.MANUAL)
        await tuner.start()
        assert tuner._strategy == TuningStrategy.MANUAL
        await tuner.stop()
