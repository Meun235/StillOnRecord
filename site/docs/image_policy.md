# Image policy

Still on Record hosts its own images.

Text goes stale. For many people an atrocity does not become real until they see it, and the photographic record is evidence in its own right: the liberation photographs from Bergen-Belsen and Nordhausen did more to establish what happened than any affidavit. A project that refuses to show any of that is not being careful, it is being squeamish, and it leaves the strongest evidence it has on the table.

So the test is not whether an image is hard to look at. It is what the image is doing there.

---

## The test

Two questions, in order.

**1. Does this image document something the record needs?** Scale, conditions, method, the state of a place, the fact of a mass grave. If yes, it is publishable, however difficult.

**2. Would a reader's interest in it be evidentiary or appetitive?** If the image adds nothing a less graphic one would not, and its pull is the suffering itself, it fails.

An image can be extremely hard to look at and pass. An image can be mild and fail. The difficulty is not the criterion.

---

## Tiers

Tiers set **placement**, not permission. Everything in A, B and C is publishable.

**Tier A — shown inline.**
- The site as it is today: memorials, ruins, buildings, landscape, plaques, grave markers.
- Documents: judgment pages, archive folios, register entries, orders, maps, plans.
- Objects, buildings and infrastructure without people.
- Photographs taken by the project itself.

**Tier B — shown inline, caption carries the context.**
- Historical photographs of places, buildings and infrastructure.
- Convicted perpetrators, from a court or press source.
- Groups, processions, deportations, where no individual is singled out in extremity.
- Survivors photographed after liberation, clothed, where dignity is intact.

**Tier C — published, behind a click.**
- The dead, including mass graves, liberation photographs, and exhumations.
- Emaciation, injury, and the physical condition of victims.
- Killing in progress, where the photograph is the documentation of the method.
- Children, where the image meets the test above. Their presence is part of what happened and hiding it falsifies the record.

Tier C images never appear on the landing page, in the map panel, in a thumbnail, in a preview card, or in a search result. They sit on the record page behind a control that states what the image shows before it is opened. Nobody arrives at one by accident.

**Tier D — refused.**
- Sexualised imagery, and forced nudity where another image documents the same fact. Where a perpetrator photograph of forced undress is genuinely the only documentation of a killing method, it goes to Tier C with the reason written on the record.
- Photographs of identifiable victims of medical experimentation, where the image was produced as research material. Publishing those completes the work the perpetrator started.
- Images whose only content is spectacle: no place, no method, no scale, nothing established.
- Identifiable living people in distress, without consent.
- Any image published against the stated wishes of a survivor, a subject, or a family.

---

## Captioning

Every image carries what it shows, when, who took it, and why it is on this record. For Tier C the caption must be readable before the image is opened.

For any historical image, name the photographer or the originating body. Most surviving photographs of atrocity were made by the people committing it, for their own purposes. Publishing one uncaptioned reproduces the perpetrator's framing and presents it as neutral record. Naming the source breaks that, and it is the single most important line in this document.

Where a victim's name is known, use it. Anonymous captioning turns a person into an illustration of a category.

Where the image was made at liberation, say so. There is a moral difference between a photograph taken by an SS officer and one taken by a British Army film unit at Belsen, and the caption should carry it.

---

## Licensing

An image is published only if its licence is one of `own`, `public_domain`, `cc0`, `cc_by`, `cc_by_sa`, or `permission` with the terms recorded. Anything else is not published. "Found on the internet" is not a licence and neither is "no copyright notice".

**A faithful reproduction of a public domain image is itself public domain** under Article 14 of the EU DSM Directive. A museum's scan of a 1940s photograph cannot attract fresh copyright, whatever their terms page says. They may restrict access by contract; they cannot restrict the image.

**"Photographer unknown" is not "author unknown" in law.** Anonymous works run 70 years from publication; works whose author has simply not been identified run life plus 70. Identify, or treat as protected.

Useful open sources: US federal government work, public domain worldwide, which covers Army Signal Corps, NARA and Nuremberg exhibits. The Bundesarchiv tranche released under CC BY-SA 3.0 DE. Imperial War Museum non-commercial material, terms per item.

---

## Living people and recent events

Dutch *portretrecht* gives a recognisable person a say in the use of their image. For anything within living memory, and certainly after 1990, assume an identifiable subject must consent, and record it.

Images supplied by a survivor or a family carry whatever terms they set, and those terms override everything above.

---

## Removal

A survivor, a subject, or a descendant may ask for an image to come down. The request is honoured first and discussed afterwards. The record stays; the image goes.

This is not a legal obligation in most cases. It is the condition of doing this work without becoming the thing the work is about.

---

## Fields

| Field | Contents |
|---|---|
| `image_file` | Path within the repository. No hotlinking. |
| `image_caption` | What it shows, when, who took it, why it is here. |
| `image_credit` | The credit line the licence requires. |
| `image_licence` | `own`, `public_domain`, `cc0`, `cc_by`, `cc_by_sa`, `permission`. |
| `image_source_url` | Where it came from, so the claim can be checked. |
| `image_tier` | `A`, `B` or `C`. Tier D is never published. |
| `image_warning` | Tier C only. One line naming what the image shows, displayed before it opens. |

The build refuses an image missing a caption, a credit or a recognised licence, and refuses a Tier C image with no warning line.
