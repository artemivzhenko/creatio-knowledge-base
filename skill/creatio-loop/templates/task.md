# 012 Shipment label

Written by the human, in any form and language; the folder number is the task id. What follows is
an example.

When an order ships, the warehouse needs a label code on the shipment: the shipment type in
capitals, a dash, the shipment number padded to four digits (`PARCEL-0007`). The code is filled
automatically when the shipment is created and must not be editable once the status is Shipped.
A process should exist that returns the label for a given shipment id, so the integration team
can call it.
