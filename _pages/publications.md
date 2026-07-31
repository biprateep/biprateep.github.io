---
layout: page
permalink: /publications/
title: Publications
description: Publications by author role, in reverse chronological order.
nav: true
nav_order: 2
---

<!-- _pages/publications.md -->

An up-to-date list is available on [NASA ADS](https://ui.adsabs.harvard.edu/search/q=orcid%3A0000-0002-5665-7912&sort=date%20desc%2C%20bibcode%20desc) and [Google Scholar](https://scholar.google.com/citations?user=qc6CJjYAAAAJ).

## Lead / Significant Contributing Author

<div class="publications">

{% bibliography --query @*[lead=true] %}

</div>

## Contributing Author

<div class="publications">

{% bibliography --query @*[lead!=true] %}

</div>
