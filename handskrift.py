import json
import random
import time

import requests
from IPython.core.display import HTML
from lxml import etree
from requests_toolbelt.multipart.encoder import MultipartEncoder

### funksjoner for arbeid med håndskrifter fra nb.no i Transkribus


def iiif_manifest(urn):
    r = requests.get("https://api.nb.no/catalog/v1/iiif/{urn}/manifest".format(urn=urn))
    return r.json()


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
        except:
            continue
    return pageDict


def lastopp_transkribus(collId="", s=None, sesamids=None):
    """last opp dokumenter fra nb.no til en collection i transkribus"""

    if s == None:
        print("Har du glemt å logge inn?")
        return

    skipped = []
    for sesamid in sesamids:
        fail = False
        print("Sesamid", sesamid)
        manifest = iiif_manifest(sesamid)
        pages = get_pages(manifest)
        files = download_pages(pages)

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
            # parse and get upload ID
            response = etree.fromstring(cont.content)
            uploadId = response.xpath("//uploadId/text()")[0]
            print("- successfully uploaded metadata, got id", uploadId)
        except:
            print("-- failed to get upload ID, skipping", sesamid)
            skipped.append(sesamid)
            continue

        # loop through files
        for key in sorted(files):
            print(key)

            mp_encoder = MultipartEncoder(
                fields={"img": (key, files[key], "application/octet-stream")}
            )

            try:
                cont = s.put(
                    "https://transkribus.eu/TrpServer/rest/uploads/" + uploadId,
                    data=mp_encoder,
                    headers={"Content-Type": mp_encoder.content_type},
                )
            except:
                print("-- failed to upload", key)
                fail = True
                break
            time.sleep(random.randint(0, 2))
        if fail == False:
            print("- done!")
        else:
            skipped.append(sesamid)
            print("-- failed to upload file in ", sesamid, "skipping this sesamid")
    print("Skipped sesamids:", skipped)


def la_transkribus(collId="", docIds=[], s=None):
    """Layoutanalyse for dokumenter i en collection"""

    if s == None:
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
            cont = s.post(
                "https://transkribus.eu/TrpServer/rest/LA?collId=" + collId,
                json=LAObj,
                headers={"Content-type": "application/json"},
            )
        except:
            print("-- failed to trigger LA for docId ", docId)
            continue


def htr_transkribus(collId="", modelId="", docIds=[], s=None):
    """HTR+ tekstgjenkjenning for dokumenter i en collection med gitt modell"""

    if s == None:
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
            htr = s.post(
                "https://transkribus.eu/TrpServer/rest/recognition/"
                + collId
                + "/"
                + modelId
                + "/htrCITlab",
                json=htrObj,
                headers={"Content-type": "application/json"},
            )
        except:
            print("-- failed to trigger HTR for docId ", docId)
            continue


def pylaia_transkribus(collId="", modelId="", s=None, docids=None):
    """pylaia tekstgjenkjenning for dokumenter i en collection med gitt modell"""

    if s == None:
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
            htr = s.post(
                "https://transkribus.eu/TrpServer/rest/pylaia/"
                + collId
                + "/"
                + modelId
                + "/recognition",
                json=PylaiaObj,
                headers={"Content-type": "application/json"},
            )
        except:
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

    while next_page == True:
        try:
            link = obj["_links"]["next"]["href"]
        except:
            next_page = False
            continue

        print(counter)
        counter += 1
        r = requests.get(link)
        obj = r.json()
        items = get_items_metadata(obj)
        itemDict.update(items)
        time.sleep(0)
    sesamids = []
    for key in itemDict:
        sesamids.append(key)
    return sesamids


def save_sesamids(sesamids, filename="sesamids.json"):
    with open(filename, "w") as file:
        for key in sesamids:
            try:
                file.write(key + "\n")
            except:
                pass
