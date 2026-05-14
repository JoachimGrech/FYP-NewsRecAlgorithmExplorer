import re
import sys

new_refs = """[1] European Commission, “Media & News Survey 2023,” europa.eu, 2023. Available: https://europa.eu/eurobarometer/surveys/detail/3153. [Accessed: Sep. 26, 2025]
[2] European Commission, “Social Media Survey 2025,” europa.eu, 2025. Available: https://europa.eu/eurobarometer/surveys/detail/3592. [Accessed: Nov. 19, 2025]
[3] Bertelsmann Stiftung, “What Europe Knows and Thinks About Algorithms,” bertelsmann-stiftung.de, 2019. Available: https://www.bertelsmann-stiftung.de/fileadmin/files/BSt/Publikationen/GrauePublikationen/WhatEuropeKnowsAndThinkAboutAlgorithm.pdf. [Accessed: Sep. 26, 2025].
[4] NVIDIA, “Recommendation System,” NVIDIA Glossary, 2024. [Online]. Available: https://www.nvidia.com/en-us/glossary/recommendation-system/
[5] F. Ricci, L. Rokach, and B. Shapira, Recommender Systems Handbook, Springer, 2015.
[6] J. B. Schafer, D. Frankowski, J. Herlocker, and S. Sen, “Collaborative Filtering Recommender Systems,” in The Adaptive Web, Springer, 2007, pp. 291–324.
[7] Y. Koren, R. Bell, and C. Volinsky, “Matrix Factorization Techniques for Recommender Systems,” Computer, vol. 42, no. 8, pp. 30–37, 2009.
[8] M. Pazzani and D. Billsus, “Content-based Recommendation Systems,” in The Adaptive Web, Springer, 2007, pp. 325–341.
[9] R. Burke, “Hybrid Recommender Systems: Survey and Experiments,” User Modeling and User-Adapted Interaction, vol. 12, no. 4, pp. 331–370, 2002.
[10] A. Das, M. Datar, A. Garg, and S. Rajaram, “Google News Personalization: Scalable Online Collaborative Filtering,” in Proc. WWW, 2007, pp. 271–280.
[11] J. Liu, P. Dolan, and E. R. Pedersen, “Personalized News Recommendation Based on Click Behavior,” in Proc. IUI, 2010, pp. 31–40.
[12] D. M. Blei, A. Y. Ng, and M. I. Jordan, “Latent Dirichlet Allocation,” Journal of Machine Learning Research, vol. 3, pp. 993–1022, 2003.
[13] J. Devlin, M. Chang, K. Lee, and K. Toutanova, “BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding,” arXiv:1810.04805, 2019.
[14] E. Pariser, The Filter Bubble, Penguin, 2011.
[15] S. Flaxman, S. Goel, and J. Rao, “Filter Bubbles, Echo Chambers, and Online News Consumption,” Quarterly Journal of Economics, vol. 131, no. 2, pp. 665–704, 2016.
[16] TensorFlow Playground, “Interactive Neural Network Visualizer.” [Online]. Available: https://playground.tensorflow.org/
[17] M. D. Ekstrand et al., “LensKit for Research: Tools for Recommender System Experiments,” in Proc. RecSys, 2022.
[18] Y. Zhang and X. Chen, “Explainable Recommendation: A Survey and New Perspectives,” Foundations and Trends in Information Retrieval, vol. 14, no. 1, pp. 1–101, 2020.
[19] C. O’Neil, Weapons of Math Destruction, Crown, 2016.
[20] Z. Tufekci, “Algorithmic Harms Beyond Facebook and Google,” First Monday, vol. 20, no. 11, 2015.
[21] T. Gillespie, “The Relevance of Algorithms,” in Media Technologies, MIT Press, 2014.
[22] N. Tintarev and J. Masthoff, “Explaining Recommendations: Design and Evaluation,” in Recommender Systems Handbook, F. Ricci, L. Rokach, and B. Shapira, Eds. Boston, MA, USA: Springer, 2015, pp. 353–382.
[23] J. L. Herlocker, J. A. Konstan, and J. Riedl, “Explaining Collaborative Filtering Recommendations,” in Proc. ACM Conf. Computer Supported Cooperative Work, Philadelphia, PA, USA, 2000, pp. 241–250.
[24] P. W. Koh and P. Liang, “Understanding Black-box Predictions via Influence Functions,” in Proc. 34th Int. Conf. Machine Learning (ICML), Sydney, Australia, 2017, pp. 1885–1894.
[25] N. Reimers and I. Gurevych, “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks,” in Proc. Empirical Methods in Natural Language Processing (EMNLP), 2019.
[26] M. Grootendorst, “BERTopic: Neural topic modeling with a class-based TF-IDF procedure,” arXiv preprint arXiv:2203.05794, 2022.
[27] C. M. Bishop, Pattern Recognition and Machine Learning, Springer, 2006.
[28] F. Gedikli, D. Jannach, and M. Ge, “How should I explain? A comparison of different explanation types for recommender systems,” International Journal of Human-Computer Studies, vol. 72, no. 4, pp. 367–382, 2014.
[29] P. Kouki, J. Schaffer, J. Pujara, J. O’Donovan, and L. Getoor, “Personalized explanations for hybrid recommender systems,” in Proc. 24th International Conference on Intelligent User Interfaces, 2019, pp. 379–390."""

mapping = {
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
    11: 11, 12: 12, 13: 13,
    15: 14, 16: 15,
    20: 18, 21: 16, 22: 24, 23: 17, 24: 18, 25: 19, 26: 20,
    27: 21, 28: 18, 29: 22, 30: 23, 31: 24, 32: 25, 33: 26, 34: 27
}

with open('FYP_Report_utf8.txt', 'r', encoding='utf-8') as f:
    text = f.read()

refs_start = text.find('REFERENCES')
body = text[:refs_start]

def replace_citation(match):
    num = int(match.group(1))
    if num in mapping:
        return f"[{mapping[num]}]"
    return match.group(0) # Unchanged if not mapped

new_body = re.sub(r'\[(\d+)\]', replace_citation, body)

new_body = new_body.replace("Chen and Zhang argue that", "Zhang and Chen argue that")

new_text = new_body + "REFERENCES\n" + new_refs + "\n"

with open('FYP_Report_utf8.txt', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Applied new references mapping fully.")
