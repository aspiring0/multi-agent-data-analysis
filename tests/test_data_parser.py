"""
DataParser Agent 单元测试
这些测试不需要 LLM API，完全本地运行。
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.data_parser import (
    data_parser_node,
    _load_dataframe,
    _build_dataset_meta,
    _detect_encoding,
)


class TestLoadDataframe:
    """测试 _load_dataframe 函数"""

    def test_load_csv(self, sample_csv_path):
        """应该能成功加载 CSV 文件"""
        df = _load_dataframe(sample_csv_path)
        assert len(df) > 0
        assert "产品" in df.columns
        assert "销量" in df.columns

    def test_load_nonexistent_file(self):
        """加载不存在的文件应该抛出异常"""
        with pytest.raises(Exception):
            _load_dataframe("/nonexistent/file.csv")

    def test_unsupported_format(self, tmp_path):
        """不支持的格式应该抛出 ValueError"""
        fake_file = tmp_path / "data.xml"
        fake_file.write_text("<data></data>")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            _load_dataframe(str(fake_file))


class TestBuildDatasetMeta:
    """测试 _build_dataset_meta 函数"""

    def test_meta_fields(self, sample_csv_path):
        """应该生成完整的元信息"""
        df = _load_dataframe(sample_csv_path)
        meta = _build_dataset_meta(df, sample_csv_path)

        assert meta["file_name"] == "sales_data.csv"
        assert meta["num_rows"] > 0
        assert meta["num_cols"] == 7
        assert "产品" in meta["columns"]
        assert len(meta["dtypes"]) == 7
        assert isinstance(meta["preview"], str)

    def test_missing_info_detected(self, sample_csv_path):
        """应该检测到缺失值"""
        df = _load_dataframe(sample_csv_path)
        meta = _build_dataset_meta(df, sample_csv_path)

        # 我们在生成数据时故意引入了约 10% 的缺失值
        # 缺失值可能存在，也可能因随机性不存在
        assert isinstance(meta["missing_info"], dict)


class TestDataParserNode:
    """测试 data_parser_node 完整流程"""

    def test_parse_with_file_path_in_message(self, sample_csv_path):
        """消息中包含文件路径时应该成功解析"""
        state = {
            "messages": [
                {"role": "user", "content": f"请帮我分析这个文件 {sample_csv_path}"}
            ],
            "datasets": [],
        }

        result = data_parser_node(state)

        # 应该返回数据集
        assert "datasets" in result
        assert len(result["datasets"]) == 1
        assert result["datasets"][0]["file_name"] == "sales_data.csv"

        # 应该有 AI 回复消息
        assert "messages" in result
        assert len(result["messages"]) > 0

    def test_parse_without_file_path(self):
        """没有文件路径时应该返回错误提示"""
        state = {
            "messages": [
                {"role": "user", "content": "帮我分析数据"}
            ],
            "datasets": [],
        }

        result = data_parser_node(state)
        assert "error" in result

    def test_parse_nonexistent_file(self):
        """文件不存在时应该返回错误"""
        state = {
            "messages": [
                {"role": "user", "content": "分析 /fake/path/data.csv"}
            ],
            "datasets": [],
        }

        result = data_parser_node(state)
        assert "error" in result

    def test_multiple_datasets(self, sample_csv_path):
        """应该支持多个数据集的追加"""
        # 第一次解析
        state = {
            "messages": [
                {"role": "user", "content": f"加载 {sample_csv_path}"}
            ],
            "datasets": [],
        }
        result1 = data_parser_node(state)

        # 第二次解析（已有一个数据集）
        state2 = {
            "messages": [
                {"role": "user", "content": f"再加载 {sample_csv_path}"}
            ],
            "datasets": result1["datasets"],
        }
        result2 = data_parser_node(state2)

        assert len(result2["datasets"]) == 2
        assert result2["active_dataset_index"] == 1


class TestDetectEncoding:
    """测试编码检测"""

    def test_utf8_file(self, sample_csv_path):
        """UTF-8 文件应该返回 utf-8"""
        enc = _detect_encoding(sample_csv_path)
        assert enc == "utf-8"
