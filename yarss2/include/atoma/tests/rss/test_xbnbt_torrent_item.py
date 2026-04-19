from datetime import datetime

from dateutil.tz import tzutc

from atoma.rss import (
    RSSChannel, RSSItem, RSSEnclosure, RSSSource, RSSTorrent, RSSTorrentItem, RSSTorrentItemElem, RSSImage, parse_rss_file
)


def test_xbnbt_torrent_item():
    item_1 = RSSItem(
        title='FreeBSD-9.0-RELEASE-amd64-all',
        link='http://torrents.FreeBSD.org:8080/stats.html?info_hash=6d53e2f47a8462899639a697942384f4b133deaa',
        description='Info Hash: 6d53e2f47a8462899639a697942384f4b133deaa<br>\n\t  Size: 3.59 GB<br>\n\t  Files: 4<br>',
        author='Unknown@unknown.com',
        categories=['None'],
        comments=None,
        enclosures=[
            RSSEnclosure(
                url='http://torrents.FreeBSD.org:8080/torrents/6d53e2f47a8462899639a697942384f4b133deaa.torrent',
                length=74111,
                type='application/x-bittorrent'
            ),
        ],
        guid='6d53e2f47a8462899639a697942384f4b133deaa',
        pub_date=datetime(2012, 3, 30, 15, 13, 54, tzinfo=tzutc()),
        source=RSSSource(
            title='FreeBSD BitTorrent Tracker',
            url='http://torrents.FreeBSD.org:8080/rss.xml'
        ),
        torrent=None,
        torrent_item=RSSTorrentItem(
            infohash=RSSTorrentItemElem("Info Hash"),
            comments=None,
            infostat=RSSTorrentItemElem(title='File Information'),
            download=RSSTorrentItemElem("DL"),
            size=RSSTorrentItemElem("Size", "3.59 GB"),
            files=RSSTorrentItemElem("Files", "4"),
            seeders=RSSTorrentItemElem("Seeders", "289"),
            leechers=RSSTorrentItemElem("Leechers", "36"),
            completed=RSSTorrentItemElem("Completed", "4959"),
            infolink=None,
        ),
        content_encoded=None
    )

    expected = RSSChannel(
        title='FreeBSD BitTorrent Tracker',
        link='http://torrents.FreeBSD.org:8080/',
        description='Tracks FreeBSD.org release ISO images',
        language='en',
        copyright='FreeBSD Project',
        managing_editor='devnull@freebsd.org',
        web_master='webmaster@freebsd.org',
        pub_date=datetime(2012, 3, 30, 15, 13, 54, tzinfo=tzutc()),
        last_build_date=datetime(2012, 3, 30, 15, 13, 54, tzinfo=tzutc()),
        categories=['All Torrents'],
        generator='XBNBT 85b.1.1 SVN 335 Flat-File Release',
        docs='http://blogs.law.harvard.edu/tech/rss',
        ttl=60,
        image=RSSImage(
            url='http://torrents.freebsd.org:8080/files/images/xbnbt.png',
            title='FreeBSD BitTorrent Tracker',
            link='http://torrents.FreeBSD.org:8080/',
            width=32,
            height=32,
            description='Tracks FreeBSD.org release ISO images'
        ),
        version='2.0',
        items=[item_1],
        content_encoded=None
    )
    assert parse_rss_file('tests/rss/freebsd_xbnbt_torrentItem.xml') == expected
