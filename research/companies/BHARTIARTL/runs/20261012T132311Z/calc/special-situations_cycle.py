"""Cycle position: consolidated EBITDA history and India mobile ARPU path (inputs from Airtel quarterly reports / IR packs / results; see ledger SPS-C067..C069)."""
# INR million; basis notes: FY2010-FY2016 Indian GAAP; FY2016(IndAS)-FY2019 Ind AS pre-116; FY2020+ post Ind AS 116; FY2024+ recast for Indus consolidation
ebitda = {"FY2010":168149,"FY2011":200718,"FY2012":237123,"FY2014":278430,"FY2015":314517,"FY2016":341902,
          "FY2017":356208,"FY2018":304479,"FY2019":262937,"FY2020":371053,"FY2021":461387,"FY2022":581103,
          "FY2023":717330,"FY2024":889064,"FY2025":1049994,"FY2026":1212676}
revenue = {"FY2010":418948,"FY2011":595383,"FY2012":714508,"FY2014":857461,"FY2015":920395,"FY2016":965321,"FY2017":954684,"FY2018":836879,"FY2019":807802,
           "FY2020":875390,"FY2021":1006158,"FY2022":1165469,"FY2023":1391448,"FY2024":1643643,"FY2025":1815110,"FY2026":2109728}
arpu = [("Q4FY2011",194),("Q4FY2012",189),("Q4FY2015",198),("Q4FY2016",194),("Q4FY2017",158),("Q4FY2018",116),
        ("Q3FY2019",104),("Q4FY2019",123),("Q3FY2020",135),("Q4FY2020",154),("Q3FY2021",166),("Q4FY2022",178),
        ("Q4FY2023",193),("Q4FY2024",209),("Q4FY2025",245),("Q4FY2026",257),("Q1FY2027",264)]
print("FY | revenue | EBITDA | margin")
for k in ebitda:
    r = revenue.get(k)
    print(k, r, ebitda[k], "%.1f%%" % (100*ebitda[k]/r) if r else "n/a")
pk = max(["FY2016","FY2017","FY2018","FY2019"], key=lambda k: ebitda[k])
print("pre-trough peak (FY2016-FY2019 window):", pk, ebitda[pk], "trough FY2019", ebitda["FY2019"],
      "peak-to-trough %.1f%%" % (100*(ebitda["FY2019"]/ebitda["FY2017"]-1)))
cagr = lambda a,b,n: (b/a)**(1/n)-1
print("EBITDA CAGR FY2019->FY2026 (7y, mixed basis): %.1f%%" % (100*cagr(ebitda["FY2019"],ebitda["FY2026"],7)))
print("EBITDA CAGR FY2023->FY2026 (3y, Indus consolidated from Nov-2024): %.1f%%" % (100*cagr(ebitda["FY2023"],ebitda["FY2026"],3)))
print("EBITDA CAGR FY2010->FY2017 (7y, pre-Jio): %.1f%%" % (100*cagr(ebitda["FY2010"],ebitda["FY2017"],7)))
mx = max(a for q,a in arpu if q<"Q4FY2018" or q.startswith("Q4FY201"))
print("ARPU pre-Jio high 198 (Q4FY2015) -> trough 104 (Q3FY2019): %.1f%%" % (100*(104/198-1)))
print("ARPU trough 104 -> Q1FY2027 264: x%.2f ; vs pre-Jio high: %+.1f%%" % (264/104, 100*(264/198-1)))
print("ARPU Q4FY2025 245 -> Q1FY2027 264 (5 quarters, no headline hike): %+.1f%%" % (100*(264/245-1)))
print("ARPU CAGR Q4FY2019 123 -> Q4FY2026 257 (7y): %.1f%%" % (100*cagr(123,257,7)))
# capex intensity (SPS-C053 for FY2026; FY2024/FY2025 from same IR pack row; FY2019 from Q4FY2019 QR SPS-C067 source)
capex = {"FY2019":287427,"FY2024":489268,"FY2025":422904,"FY2026":475218}
for k,v in capex.items():
    print("capex/revenue %s %.1f%%" % (k, 100*v/revenue[k]))
print("Q1FY2027 consolidated capex/revenue %.1f%%" % (100*133860/585391))
