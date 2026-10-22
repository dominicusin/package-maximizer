"""Core coverage-gap tests: GraphBuilder, PackageGraph, objectives."""
from package_maximizer.core.graph_builder import (
    GraphBuilder,
    PackageGraph,
    build_buildtime_graph,
    build_runtime_graph,
    detect_cycles,
)
from package_maximizer.core.objective import (
    DefaultObjective,
    Objective,
    get_default_weights,
)
from package_maximizer.core.package import Package


def _pkg(name, version="1.0", depends=None, conflicts=None):
    return Package(name=name, version=version, depends=list(depends or []), conflicts=list(conflicts or []))


class TestGraphBuilderRuntime:
    def test_build_creates_nodes_and_edges(self):
        pkgs = [_pkg("nginx", depends=["libc6"]), _pkg("libc6")]
        graph = GraphBuilder().build(pkgs)
        assert "nginx" in graph.nodes
        assert "libc6" in graph.nodes
        assert graph.nodes["nginx"].depends
        assert graph.node("libc6").depends == []

    def test_build_adds_conflict_edge(self):
        pkgs = [_pkg("nginx", depends=["libc6"], conflicts=["apache2"]), _pkg("libc6"), _pkg("apache2")]
        graph = GraphBuilder().build(pkgs)
        assert ("apache2", "") in graph.nodes["nginx"].conflicts

    def test_build_runtime_graph_utility(self):
        pkgs = [_pkg("a", depends=["b"]), _pkg("b")]
        graph = build_runtime_graph(pkgs)
        assert graph.mode == "runtime"
        assert graph.cycle_found is False
        assert graph.topological_order() == ["b", "a"]

    def test_build_buildtime_graph(self):
        pkgs = [_pkg("a", depends=["b"]), _pkg("b")]
        graph = build_buildtime_graph(pkgs)
        assert graph.mode == "buildtime"
        assert graph.nodes["b"].declared_by == "a"

    def test_buildtime_edges_set_declared_by(self):
        pkgs = [_pkg("a", depends=["b"]), _pkg("b")]
        graph = GraphBuilder(mode="buildtime").build(pkgs)
        assert graph.nodes["b"].declared_by == "a"

    def test_topological_order_no_cycle(self):
        pkgs = [_pkg("a", depends=["b"]), _pkg("b")]
        graph = GraphBuilder().build(pkgs)
        assert graph.topological_order() == ["b", "a"]

    def test_topological_order_cycle(self):
        pkgs = [_pkg("a", depends=["b"]), _pkg("b", depends=["a"])]
        graph = GraphBuilder().build(pkgs)
        order = graph.topological_order()
        assert order == []
        assert graph.cycle_found is True

    def test_build_finds_cycle(self):
        pkgs = [_pkg("a", depends=["b"]), _pkg("b", depends=["a"])]
        graph = GraphBuilder().build(pkgs)
        assert graph.topological_order() == []
        assert graph.cycle_found is True

    def test_py314_cyclic_graph(self):
        pkgs = [
            Package(name="a", version="1", depends=["b"]),
            Package(name="b", version="1", depends=["c"]),
            Package(name="c", version="1", depends=["a"]),
        ]
        graph = GraphBuilder().build(pkgs)
        assert graph.topological_order() == []
        assert graph.cycle_found is True

    def test_to_dict(self):
        graph = GraphBuilder().build([_pkg("a")])
        data = graph.to_dict()
        assert data["mode"] == "runtime"
        assert len(data["nodes"]) == 1
        assert "depends" in data["nodes"][0]
        assert "conflicts" in data["nodes"][0]

    def test_invalid_mode_raises(self):
        import pytest
        with pytest.raises(ValueError):
            GraphBuilder(mode="invalid")


class TestPackageGraph:
    def test_node_lookup(self):
        graph = GraphBuilder().build([_pkg("a")])
        assert graph.node("a") is not None
        assert graph.node("b") is None

    def test_add_node_idempotent(self):
        graph = GraphBuilder().build([_pkg("a"), _pkg("a")])
        assert len(graph.nodes) == 1

    def test_conflicts_set(self):
        pkgs = [_pkg("a", conflicts=["b"]), _pkg("b")]
        graph = GraphBuilder().build(pkgs)
        assert ("b", "") in graph.nodes["a"].conflicts


class TestDetectCycles:
    def test_cycle_payload(self):
        import json
        payload = json.dumps({"nodes": [{"name": "a", "cycle_found": True}]})
        assert detect_cycles(payload) == [["a"]]

    def test_no_payload(self):
        assert detect_cycles(None) == []
        assert detect_cycles("") == []

    def test_bad_json(self):
        assert detect_cycles("not json") == []

    def test_cycle_not_found(self):
        import json
        payload = json.dumps({"nodes": [{"name": "a", "cycle_found": False}]})
        assert detect_cycles(payload) == []


class TestObjective:
    def test_is_weighted_count(self):
        obj = Objective(name="count")
        assert obj.is_weighted() is False

    def test_is_weighted_weighted(self):
        assert Objective(name="weighted").is_weighted() is True

    def test_is_weighted_user_defined(self):
        assert Objective(name="user_defined").is_weighted() is True

    def test_weight_for_explicit(self):
        pkg = Package(name="vim", version="9.0")
        obj = Objective()
        assert obj.weight_for(pkg, explicit={"vim": 2.0}) == 2.0

    def test_weight_for_default_priority(self):
        pkg = Package(name="vim", version="9.0")
        obj = Objective(priority_key="priority")
        assert obj.weight_for(pkg) == 1.0

    def test_weight_for_default_weight(self):
        pkg = Package(name="vim")
        assert Objective().weight_for(pkg) == 1.0

    def test_weight_for_type_error(self):
        pkg = Package(name="vim", version="9.0")
        obj = Objective(priority_key="priority")
        assert obj.weight_for(pkg) == 1.0

    def test_weight_for_no_priority_key(self):
        pkg = Package(name="vim")
        obj = Objective(priority_key="nope")
        assert obj.weight_for(pkg) == obj.default_weight

    def test_get_default_weights(self):
        w = get_default_weights()
        assert w == {"count": 1.0, "weighted": 1.0, "user_defined": 1.0}

    def test_default_objective_alias(self):
        assert DefaultObjective is Objective
        assert DefaultObjective().name == "count"
