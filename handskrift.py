"""Hjelpefunksjoner for arbeid med håndskriftsgjenkjenning av bilder fra nb.no i Transkribus"""

import json
import random
import time

import requests
from lxml import etree
from requests_toolbelt.multipart.encoder import MultipartEncoder


def iiif_manifest(urn):
    r = requests.get("https://api.nb.no/catalog/v1/iiif/{urn}/manifest".format(urn=urn))
    content = r.json()
    if content.get("status") == "NOT_FOUND":
        print("-- Fant ikke IIIF-manifestet for ", urn)
    return content


def get_pages(manifest):
    try:
        pages = [
            page["images"][0]["resource"]["@id"]
            for page in manifest["sequences"][0]["canvases"]
        ]
    except KeyError:
        pages = []
    return pages


def download_pages(pages, wait=1):
    pageDict = dict()
    for page in pages:
        try:
            filename = page.split("/")[6].split(":")[-1] + ".jpg"
            r = requests.get(page, stream=True)
            pageDict[filename] = r.content
            time.sleep(wait)
            r.raise_for_status()
        except requests.exceptions.RequestException:
            continue
    return pageDict


def number_of_pages_total(response):
    """Check how many pages were uploaded from the request response"""
    number = response.xpath("//nrOfPagesTotal/text()")[0]
    return int(number)


def lastopp_transkribus(collId="", s=None, sesamids=None):
    """last opp dokumenter fra nb.no til en collection i transkribus"""

    if s is None:
        print("Har du glemt å logge inn?")
        return

    # Samle opp sesamid for brev som ikke blir lastet opp
    skipped = []
    for sesamid in sesamids:
        # fail = False
        print("Sesamid", sesamid)
        # Hent bilder fra Nettbiblioteket
        manifest = iiif_manifest(sesamid)
        pages = get_pages(manifest)
        files = download_pages(pages)

        if len(files) == 0 or len(pages) == 0:
            print("-- Found no image files or pages for sesamid, skipping", sesamid)
            skipped.append(sesamid)
            continue

        # Last opp metadata for filene til Transkribus
        pages_metadata = [
            {"fileName": val, "pageNr": idx + 1}
            for idx, val in enumerate(sorted(files))
        ]
        uploadObj = {"md": {"title": sesamid}, "pageList": {"pages": pages_metadata}}
        headers = {"Content-type": "application/json"}
        try:
            cont = s.post(
                "https://transkribus.eu/TrpServer/rest/uploads?collId=" + str(collId),
                json=uploadObj,
                headers=headers,
            )
            # parse response xml and get upload ID
            response = etree.fromstring(cont.content)
            uploadId = response.xpath("//uploadId/text()")[0]
            if number_of_pages_total(response) > 0:
                print("- uploaded metadata with uploadId", uploadId)
            else:
                print("-- No pages uploaded, skipping", sesamid)
                skipped.append(sesamid)
                continue
        except requests.exceptions.RequestException:
            print("-- failed to get upload ID, skipping", sesamid)
            skipped.append(sesamid)
            continue

        # Upload image file for each page to Transkribus
        for key in sorted(files):
            mp_encoder = MultipartEncoder(
                fields={"img": (key, files[key], "application/octet-stream")}
            )

            try:
                cont = s.put(
                    "https://transkribus.eu/TrpServer/rest/uploads/" + uploadId,
                    data=mp_encoder,
                    headers={"Content-Type": mp_encoder.content_type},
                )
                cont.raise_for_status()
            except requests.exceptions.RequestException:
                print("-- failed to upload", key, "skipping this sesamid")
                print("  ", cont.text)
                skipped.append(sesamid)
                break  # skip to next sesamid
            time.sleep(random.randint(0, 2))  # Wait for the server before next upload
            print("- done uploading file", key)
        # skipped.append(sesamid)
        # print("-- failed to upload file in ", sesamid, "skipping this sesamid")
    print("Skipped sesamids:", skipped)


def la_transkribus(collId="", docIds=[], s=None):
    """Layoutanalyse for dokumenter i en collection"""

    if s is None:
        print("Har du glemt å logge inn?")
        return

    docs = s.get(
        "https://transkribus.eu/TrpServer/rest/collections/" + collId + "/list"
    )
    if not docIds:
        docIds = [x["docId"] for x in json.loads(docs.content)]

    for docId in docIds:
        LAObj = {"docList": {"docs": [{"docId": docId}]}}

        try:
            print("- triggering LA for docId ", docId)
            s.post(
                "https://transkribus.eu/TrpServer/rest/LA?collId=" + collId,
                json=LAObj,
                headers={"Content-type": "application/json"},
            )
        except requests.exceptions.RequestException:
            print("-- failed to trigger LA for docId ", docId)
            continue


def htr_transkribus(collId="", modelId="", docIds=[], s=None):
    """HTR+ tekstgjenkjenning for dokumenter i en collection med gitt modell"""

    if s is None:
        print("Har du glemt å logge inn?")
        return

    docs = s.get(
        "https://transkribus.eu/TrpServer/rest/collections/" + collId + "/list"
    )
    if not docIds:
        docIds = [x["docId"] for x in json.loads(docs.content)]

    for docId in docIds:
        htrObj = {"docId": docId}

        try:
            print("- triggering HTR for docId ", docId)
            s.post(
                "https://transkribus.eu/TrpServer/rest/recognition/"
                + collId
                + "/"
                + modelId
                + "/htrCITlab",
                json=htrObj,
                headers={"Content-type": "application/json"},
            )
        except requests.exceptions.RequestException:
            print("-- failed to trigger HTR for docId ", docId)
            continue


def pylaia_transkribus(collId="", modelId="", s=None, docids=None):
    """pylaia tekstgjenkjenning for dokumenter i en collection med gitt modell"""

    if s is None:
        print("Har du glemt å logge inn?")
        return

    if docids is None:
        docs = s.get(
            "https://transkribus.eu/TrpServer/rest/collections/" + collId + "/list"
        )
        docIds = [x["docId"] for x in json.loads(docs.content)]
    else:
        docIds = docids

    for docId in docIds:
        PylaiaObj = {"docId": docId}

        try:
            print("- triggering Pylaia for docId ", docId)
            s.post(
                "https://transkribus.eu/TrpServer/rest/pylaia/"
                + collId
                + "/"
                + modelId
                + "/recognition",
                json=PylaiaObj,
                headers={"Content-type": "application/json"},
            )
        except requests.exceptions.RequestException:
            print("-- failed to trigger Pylaia for docId ", docId)
            continue


def get_attribute(data, attribute, default_value=""):
    if data:
        if attribute in data:
            return data[attribute]
        else:
            return default_value
    else:
        return default_value


def get_items_metadata(jsonObj):
    items = dict()
    if "_embedded" in jsonObj:
        if "items" in jsonObj["_embedded"]:
            for item in jsonObj["_embedded"]["items"]:
                sesamid = item["id"]
                items[sesamid] = {}
                if "metadata" in item:
                    items[sesamid]["creators"] = get_attribute(
                        item["metadata"], "creators"
                    )
                    items[sesamid]["title"] = get_attribute(item["metadata"], "title")
                    items[sesamid]["identifiers"] = get_attribute(
                        item["metadata"], "identifiers"
                    )
                if "accessInfo" in item:
                    items[sesamid]["isDigital"] = get_attribute(
                        item["accessInfo"], "isDigital"
                    )
        return items
    else:
        return None


def run_query(query):
    """Kjør et søk på sesamid"""
    itemDict = dict()
    next_page = True
    counter = 1
    r = requests.get("https://api.nb.no/catalog/v1/items", params=query)
    obj = r.json()
    items = get_items_metadata(obj)
    itemDict.update(items)
    print(
        obj["page"]["totalElements"],
        "elementer totalt i",
        obj["page"]["totalPages"],
        "bolker",
    )

    while next_page:
        try:
            link = obj["_links"]["next"]["href"]
        except KeyError:
            next_page = False
            continue

        print(".", end="")
        counter += 1
        r = requests.get(link)
        obj = r.json()
        items = get_items_metadata(obj)
        itemDict.update(items)
        time.sleep(0)
    print("Ferdig")
    sesamids = []
    for key in itemDict:
        sesamids.append(key)
    return sesamids


def save_sesamids(sesamids, filename="sesamids.json"):
    with open(filename, "w") as file:
        for key in sesamids:
            file.write(key + "\n")


def did_pages_upload(response):
    pageUploaded = response.xpath("//pageList/pages/pageUploaded")
    return [eval(status.text.title()) for status in pageUploaded]


def get_jobs(session):
    jobs = "https://transkribus.eu/TrpServer/rest/jobs/list"
    jobslist = session.get(jobs).json()
    return jobslist


def get_jobid_for_sesamid(jobslist, sesamid):
    for job in jobslist:
        if job["docTitle"] == sesamid:
            return job["jobId"]


def is_success(jobid, session):
    jobstatus = f"https://transkribus.eu/TrpServer/rest/jobs/{jobid}"
    status = session.get(jobstatus).json()
    return status.get("success")


def check_status(sesamids):
    skipped = []
    jobslist = get_jobs()
    for sesamid in sesamids:
        jobid = get_jobid_for_sesamid(jobslist, sesamid)
        if jobid:
            success = is_success(jobid)
            if success:
                print(f"{sesamid} har jobId {jobid} og ble lastet opp: {success}")
            if not success:
                print(f"-- Hoppet over {sesamid}")
                skipped.append(sesamid)
        else:
            print(f"Ingen jobb funnet for {sesamid}")
            skipped.append(sesamid)
    return skipped


def get_collection_id(collection_name: str, session: requests.Session) -> str:
    """Get the Transkribus collection ID for a given collection name"""
    response = session.get("https://transkribus.eu/TrpServer/rest/collections")
    collections = response.json()

    for col in collections["trpCollection"]:
        if col.get("colName") == collection_name:
            coll_id = col.get("colId")
            print(f"Collection ID for {collection_name}: {coll_id}")
            return coll_id
    print(f"Collection {collection_name} not found.")


def get_sesamids_from_transkribus_collection(
    collection_id: str, session: requests.Session
) -> list:
    """Fetch sesamids from a Transkribus collection."""
    response = session.get(
        f"https://transkribus.eu/TrpServer/rest/collections/{collection_id}/list"
    )
    collection_docs = response.json()
    sesamids = [doc["title"] for doc in collection_docs]
    return sesamids


def filter_sesamids(library_ids: list[str], transkribus_ids: list[str]) -> list[str]:
    """Extract IDs of the digitized documents that are in the library but not in Transkribus."""
    new_docs = list(set(library_ids).difference(set(transkribus_ids)))
    return new_docs


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Last opp bilder fra Nettbiblioteket til Transkribus"
    )
    parser.add_argument(
        "-c", "--collection", help="Collection ID i Transkribus", required=True
    )
    parser.add_argument(
        "-u", "--username", help="Brukernavn i Transkribus", required=True
    )
    parser.add_argument("-p", "--password", help="Passord i Transkribus", required=True)
    parser.add_argument(
        "-i",
        "--sesamids",
        type=Path,
        help="Fil med sesamids som skal lastes opp. Én ID per linje",
        required=True,
    )

    args = parser.parse_args()

    session = requests.Session()
    login_response = session.post(
        "https://transkribus.eu/TrpServer/rest/auth/login",
        data={"user": args.username, "pw": args.password},
    )

    if login_response.ok:
        print("Du er logget inn!")
    else:
        print("OBS! Kunne ikke logge inn. Sjekk påloggingsinfoen og prøv igjen.")
        sys.exit(0)

    sesamids = args.sesamids.read_text().splitlines()
    lastopp_transkribus(collId=args.collection, s=session, sesamids=sesamids)
