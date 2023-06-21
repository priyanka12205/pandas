import pytest


@pytest.fixture
def xml_data_path(tests_io_data_path):
    return tests_io_data_path / "xml"


@pytest.fixture
def xml_books(xml_data_path):
    return xml_data_path / "books.xml"


@pytest.fixture
def xml_doc_ch_utf(xml_data_path):
    return xml_data_path / "doc_ch_utf.xml"


@pytest.fixture
def xml_baby_names(xml_data_path):
    return xml_data_path / "baby_names.xml"


@pytest.fixture
def kml_cta_rail_lines(xml_data_path):
    return xml_data_path / "cta_rail_lines.kml"


@pytest.fixture
def xsl_flatten_doc(xml_data_path):
    return xml_data_path / "flatten_doc.xsl"
