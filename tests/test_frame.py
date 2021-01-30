from heatmon.frame import Frame

EXAMPLE_PACKET_1 = b"\x4f\x02\x80\x81\x02\x00\x01\x23"
EXAMPLE_PACKET_2 = b"\x4f\x02\x80\x81\x08\x7f\x11\x7b\x22\x62\x22\x3a\x31\x61"
EXAMPLE_PACKET_3 = (
    b"\xcf\x94\xaa\xaa\xaa\xaa\x20\xb3\x45\xf9\x29\x69\x57\x0c\xb8\x28\x66\x14\xb4\xf0\x69"
    b"\xb0\x08\x71\xda\xd8\xfe\x47\xc1\xc3\x53\x83\x48\x88\x03\x7d\x58\x75\x75\x00\x00\x2a"
    b"\x00\x03\x19\x29\x3b\x31\x52\xc3\x26\xd2\x6d\xd0\x8d\x70\x1e\x4b\x68\x0d\xcb\x80"
)


def test_1():
    decoded = Frame(EXAMPLE_PACKET_1)
    assert decoded.id == b"\x80\x81"
    assert decoded.frame_type == Frame.OPEN_FRAME_TYPE
    assert not decoded.corrupt


def test_2():
    decoded = Frame(EXAMPLE_PACKET_2)
    assert decoded.id == b"\x80\x81"
    assert decoded.frame_type == Frame.OPEN_FRAME_TYPE
    assert not decoded.corrupt


def test_3():
    decoded = Frame(EXAMPLE_PACKET_3)
    assert decoded.id == b"\xaa\xaa\xaa\xaa"
    assert decoded.frame_type == Frame.SECURE_FRAME_TYPE
    assert not decoded.corrupt
