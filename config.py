htmls = "./pdfs/"
recursive = True
max_len = 200

log_files = {
    "ccapp": "./log.log",
    "cc": "../CorpusCook/log.log",
    "dist": "./ai-difference/Distinctiopus/log.log"
}

cc_corpus_path = "~/CorpusCook/manually_annotated"
dist_corpus_path = "~/ai-difference/Distinctiopus4/manual_corpus"

mixer_path = "~/CorpusCook/manually_annotated/mix_corpus_from_manual_files.py"

train_script= "~/ai-difference/Distinctiopus4/do/train_difference.sh"
allennlp_config = "~/ai-difference/Distinctiopus4/experiment_configs/elmo_lstm3_feedforward4_crf_straight_fitter.config"

dist_model_path_first = "~/ai-difference/Distinctiopus4/output/first_./experiment_configs/{config}/model.tar.gz".format(config=allennlp_config)
cc_model_path_first   = "~/CorpusCook/server/models/model_first.tar.gz"
dist_model_path_over  = "~/ai-difference/Distinctiopus4/output/over_./experiment_configs/{config}/model.tar.gz".format(config=allennlp_config)
cc_model_path_over    = "~/CorpusCook/server/models/model_over.tar.gz"
