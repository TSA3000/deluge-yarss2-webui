from datetime import datetime
from io import BytesIO
from typing import Optional, List
from xml.etree.ElementTree import Element

import attr

from .utils import (
    parse_xml, get_child, get_text, get_int, get_datetime, FeedParseError,
    try_parse_length
)

supported_rss_versions = ['2.0']


@attr.s
class RSSImage:
    url: str = attr.ib()
    title: Optional[str] = attr.ib()
    link: str = attr.ib()
    width: int = attr.ib()
    height: int = attr.ib()
    description: Optional[str] = attr.ib()


@attr.s
class RSSEnclosure:
    url: str = attr.ib()
    length: Optional[int] = attr.ib()
    type: Optional[str] = attr.ib()


@attr.s
class RSSSource:
    title: str = attr.ib()
    url: Optional[str] = attr.ib()


@attr.s
class RSSTorrent:
    filename: Optional[str] = attr.ib()
    contentlength: Optional[str] = attr.ib()
    infohash: Optional[str] = attr.ib()
    magneturi: Optional[str] = attr.ib()


@attr.s
class RSSTorrentItemElem:
    title: str = attr.ib()
    value: Optional[str] = attr.ib(default=None)


@attr.s
class RSSTorrentItem:
    infohash: Optional[RSSTorrentItemElem] = attr.ib()
    comments: Optional[RSSTorrentItemElem] = attr.ib()
    infostat: Optional[RSSTorrentItemElem] = attr.ib()
    download: Optional[RSSTorrentItemElem] = attr.ib()
    size: Optional[RSSTorrentItemElem] = attr.ib()
    files: Optional[RSSTorrentItemElem] = attr.ib()
    seeders: Optional[RSSTorrentItemElem] = attr.ib()
    leechers: Optional[RSSTorrentItemElem] = attr.ib()
    completed: Optional[RSSTorrentItemElem] = attr.ib()
    infolink: Optional[RSSTorrentItemElem] = attr.ib()


@attr.s
class RSSItem:
    title: Optional[str] = attr.ib()
    link: Optional[str] = attr.ib()
    description: Optional[str] = attr.ib()
    author: Optional[str] = attr.ib()
    categories: List[str] = attr.ib()
    comments: Optional[str] = attr.ib()
    enclosures: List[RSSEnclosure] = attr.ib()
    guid: Optional[str] = attr.ib()
    pub_date: Optional[datetime] = attr.ib()
    source: Optional[RSSSource] = attr.ib()

    # Extension
    torrent: Optional[RSSTorrent] = attr.ib()
    torrent_item: Optional[RSSTorrentItem] = attr.ib()
    content_encoded: Optional[str] = attr.ib()


@attr.s
class RSSChannel:
    title: Optional[str] = attr.ib()
    link: Optional[str] = attr.ib()
    description: Optional[str] = attr.ib()
    language: Optional[str] = attr.ib()
    copyright: Optional[str] = attr.ib()
    managing_editor: Optional[str] = attr.ib()
    web_master: Optional[str] = attr.ib()
    pub_date: Optional[datetime] = attr.ib()
    last_build_date: Optional[datetime] = attr.ib()
    categories: List[str] = attr.ib()
    generator: Optional[str] = attr.ib()
    docs: Optional[str] = attr.ib()
    ttl: Optional[int] = attr.ib()
    image: Optional[RSSImage] = attr.ib()
    version: Optional[str] = attr.ib()

    items: List[RSSItem] = attr.ib()

    # Extension
    content_encoded: Optional[str] = attr.ib()


def _get_image(element: Element, name,
               optional: bool=True) -> Optional[RSSImage]:
    child = get_child(element, name, optional)
    if child is None:
        return None

    return RSSImage(
        get_text(child, 'url', optional=False),
        get_text(child, 'title'),
        get_text(child, 'link', optional=False),
        get_int(child, 'width') or 88,
        get_int(child, 'height') or 31,
        get_text(child, 'description')
    )


def _get_source(element: Element, name,
                optional: bool=True) -> Optional[RSSSource]:
    child = get_child(element, name, optional)
    if child is None:
        return None

    return RSSSource(
        child.text.strip(),
        child.attrib.get('url'),
    )


def _get_enclosure(element: Element) -> RSSEnclosure:
    return RSSEnclosure(
        element.attrib['url'],
        try_parse_length(element.attrib.get('length')),
        element.attrib.get('type'),
    )


def _get_link(element: Element) -> Optional[str]:
    """Attempt to retrieve item link.

    Use the GUID as a fallback if it is a permalink.
    """
    link = get_text(element, 'link')
    if link is not None:
        return link

    guid = get_child(element, 'guid')
    if guid is not None and guid.attrib.get('isPermaLink') == 'true':
        return get_text(element, 'guid')

    return None


def _get_torrent_element(element: Element,
                optional: bool=True) -> Optional[RSSTorrent]:
    """
    Parse values from torrent item as defined by http://xmlns.ezrss.it/0.1/
    (stored in tests/data/feeds/xmlns.ezrss.it_0.1.dtd)
    """
    # Check if there is a torrent item (<torrent xmlns="...">)
    torrent_elem = get_child(element, 'ezrss:torrent', optional)

    # No torrent item, so try to get the fields names on the form <torrent:contentLength>
    # from the item element directly
    if torrent_elem is None:
        torrent_elem = element

    attr_names = ['fileName', 'contentLength', 'infoHash', 'magnetURI']
    params = []
    for name in attr_names:
        value = None
        elem = get_child(torrent_elem, 'ezrss:{}'.format(name))
        if elem is not None:
            value = elem.text
        params.append(value)

    # None of the attributes found
    if params.count(None) == len(attr_names):
        return None

    return RSSTorrent(*params)

def _get_torrent_item(element: Element,
                optional: bool=True) -> Optional[RSSTorrentItem]:
    """
    Parse values from torrent item as defined by namespace declaration
    xmlns:torrentItem="http://xbnbt.sourceforge.net/ns/torrentItem#"

    """
    attr_names = ['infohash', 'comments', 'infostat', 'download', 'size',
                  'files', 'seeders', 'leechers', 'completed', 'infolink']
    params = []
    for name in attr_names:
        item = None
        elem = get_child(element, 'torrentItem:{}'.format(name))
        if elem is not None:
            item = RSSTorrentItemElem(elem.attrib.get("title"), elem.text)
        params.append(item)

    # None of the attributes found
    if params.count(None) == len(attr_names):
        return None

    return RSSTorrentItem(*params)


def _get_item(element: Element) -> RSSItem:
    root = element
    title = get_text(root, 'title')
    link = _get_link(root)
    description = get_text(root, 'description')
    author = get_text(root, 'author')
    categories = [e.text for e in root.findall('category')]
    comments = get_text(root, 'comments')
    enclosure = [_get_enclosure(e) for e in root.findall('enclosure')]
    guid = get_text(root, 'guid')
    pub_date = get_datetime(root, 'pubDate')
    source = _get_source(root, 'source')
    torrent = _get_torrent_element(root)
    torrent_item = _get_torrent_item(root)
    content_encoded = get_text(root, 'content:encoded')
    return RSSItem(
        title,
        link,
        description,
        author,
        categories,
        comments,
        enclosure,
        guid,
        pub_date,
        source,
        torrent,
        torrent_item,
        content_encoded,
    )


def _parse_rss(root: Element) -> RSSChannel:
    rss_version = root.get('version')
    if supported_rss_versions and rss_version not in supported_rss_versions:
        raise FeedParseError('Cannot process RSS feed version "{}"'
                             .format(rss_version))

    root = root.find('channel')
    if root is None:
        raise FeedParseError('RSS does not have a channel')

    title = get_text(root, 'title')
    link = get_text(root, 'link')
    description = get_text(root, 'description')
    language = get_text(root, 'language')
    copyright = get_text(root, 'copyright')
    managing_editor = get_text(root, 'managingEditor')
    web_master = get_text(root, 'webMaster')
    pub_date = get_datetime(root, 'pubDate')
    last_build_date = get_datetime(root, 'lastBuildDate')
    categories = [e.text for e in root.findall('category')]
    generator = get_text(root, 'generator')
    docs = get_text(root, 'docs')
    ttl = get_int(root, 'ttl')

    image = _get_image(root, 'image')
    items = [_get_item(e) for e in root.findall('item')]

    content_encoded = get_text(root, 'content:encoded')

    return RSSChannel(
        title,
        link,
        description,
        language,
        copyright,
        managing_editor,
        web_master,
        pub_date,
        last_build_date,
        categories,
        generator,
        docs,
        ttl,
        image,
        rss_version,
        items,
        content_encoded
    )


def parse_rss_file(filename: str) -> RSSChannel:
    """Parse an RSS feed from a local XML file."""
    root = parse_xml(filename).getroot()
    return _parse_rss(root)


def parse_rss_bytes(data: bytes) -> RSSChannel:
    """Parse an RSS feed from a byte-string containing XML data."""
    root = parse_xml(BytesIO(data)).getroot()
    return _parse_rss(root)
