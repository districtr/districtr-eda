import numpy as np
import pandas as pd
import operator

def compute_align_scores(dist_changes, elec_sets, state_gdf, part_assingment, primary_elecs, \
                         black_pref_cands_prim, elec_match_dict, \
                         mean_prec_counts, geo_id):

    black_align_prim = pd.DataFrame(columns = [str(d) for d in dist_changes])
    black_align_prim["Election Set"] = elec_sets
    # print(black_pref_cands_prim.to_markdown())

    for district in dist_changes:
        # print(district)
        state_gdf["New Map"] = state_gdf.index.map(part_assingment)
        dist_prec_list =  list(state_gdf[state_gdf["New Map"] == district][geo_id])
        cand_counts_dist = mean_prec_counts[mean_prec_counts[geo_id].isin(dist_prec_list)]
        for elec in primary_elecs:
            # print(elec)
            # print((black_pref_cands_prim["Election Set"] == elec_match_dict[elec]).to_markdown())
            black_pref_cand = black_pref_cands_prim.loc[black_pref_cands_prim["Election Set"] == elec_match_dict[elec], str(district)].values[0]
            black_align_prim.at[black_align_prim["Election Set"] == elec_match_dict[elec], str(district)] = \
            sum(cand_counts_dist["BCVAP"+ '.' + black_pref_cand])/(sum(cand_counts_dist["BCVAP"+ '.' + black_pref_cand]) + sum(cand_counts_dist["WCVAP"+ '.' + black_pref_cand]) + sum(cand_counts_dist["OCVAP"+ '.' + black_pref_cand]))


    return black_align_prim


def compute_final_dist(map_winners, black_pref_cands_df,
                 black_weight_df, dist_elec_results, dist_changes,
                 cand_race_table, candidates, \
                 elec_sets, elec_set_dict, black_align_prim, \
                 mode, logit_params, logit = False, single_map = False):
    #determine if election set accrues points by district for black
    primary_winners = map_winners[map_winners["Election Type"] == 'Primary'].reset_index(drop = True)
    general_winners = map_winners[map_winners["Election Type"] == 'General'].reset_index(drop = True)

    black_pref_wins = pd.DataFrame(columns = [str(d) for d in dist_changes])
    black_pref_wins["Election Set"] = elec_sets

    primary_second_df = pd.DataFrame(columns = [str(d) for d in dist_changes])
    primary_second_df["Election Set"] = elec_sets

    primary_races = [elec_set_dict[elec_set]["Primary"] for elec_set in black_pref_cands_df["Election Set"]]
    cand_party_dict = cand_race_table.set_index("Candidates").to_dict()["Party"]


    for dist in dist_changes:
        # print(dist)
        black_pref_cands = list(black_pref_cands_df[str(dist)])
        primary_dict = primary_winners.set_index("Election Set").to_dict()[dist]
        primary_winner_list = [primary_dict[es] for es in elec_sets]

        general_dict = general_winners.set_index("Election Set").to_dict()[dist]
        general_winner_list = ["N/A" if es not in list(general_winners["Election Set"]) \
        else general_dict[es] for es in elec_sets]

        primary_race_share_dict = {primary_race:dist_elec_results[primary_race][dist] for primary_race in primary_races}
        primary_ranking = {primary_race:{key: rank for rank, key in \
                           enumerate(sorted(primary_race_share_dict[primary_race], \
                           key=primary_race_share_dict[primary_race].get, reverse=True), 1)} \
                                            for primary_race in primary_race_share_dict.keys()}

        second_place_primary = {primary_race: [cand for cand, value in primary_ranking[primary_race].items() \
                                               if primary_ranking[primary_race][cand] == 2] for primary_race in primary_races}

        primary_second_df[str(dist)] = [second_place_primary[key][0]if second_place_primary[key] != [] else "N/A" for key in second_place_primary.keys() ]


        black_pref_prim_rank = [primary_ranking[pr][bpc] for pr, bpc in zip(primary_races, black_pref_cands)]
        party_general_winner = [cand_party_dict[gw] if gw in cand_party_dict.keys() else None for gw in general_winner_list]

        #winning conditions (conditions to accrue points for election set/minority group):
        black_accrue = [(prim_win == bpc and party_win == 'D') if 'President' in prim_race else \
                        ((primary_race_share_dict[prim_race][bpc]) > .5 or (bpp_rank < 3 and party_win == 'D') or (bpp_rank == 1 and party_win == None))
                        for bpc, prim_win, party_win, bpp_rank, prim_race \
                        in zip(black_pref_cands, primary_winner_list, party_general_winner, \
                               black_pref_prim_rank, primary_races)]

        black_pref_wins[str(dist)] = black_accrue


    black_weight_df = black_weight_df.set_index("Election Set")
    black_pref_wins = black_pref_wins.set_index("Election Set")
    black_align_prim = black_align_prim.set_index("Election Set")
    black_points_accrued = black_weight_df*black_pref_wins


########################################################################################
    #Compute district probabilities: black, Latino, neither and overlap
    black_vra_prob = [0 if sum(black_weight_df[str(i)]) == 0 else sum((black_points_accrued*black_align_prim)[str(i)])/sum(black_weight_df[str(i)]) for i in dist_changes]
    #feed through logit:
    if logit == True:
        logit_coef_black = logit_params.loc[(logit_params['model_type'] == mode) & (logit_params['subgroup'] == 'Black'), 'coef'].values[0]
        logit_intercept_black = logit_params.loc[(logit_params['model_type'] == mode) & (logit_params['subgroup'] == 'Black'), 'intercept'].values[0]
        black_vra_prob = [1/(1+np.exp(-(logit_coef_black*y+logit_intercept_black))) for y in black_vra_prob]

    not_effect_vra_prob = [1-i for i in black_vra_prob]
    if single_map:
        return  dict(zip(dist_changes, zip(black_vra_prob, not_effect_vra_prob))), \
                black_pref_wins, black_points_accrued, primary_second_df, black_align_prim
    else:
        return dict(zip(dist_changes, zip(black_vra_prob, not_effect_vra_prob)))



def district_vra_effectiveness(part_assingment, data):
    #Overview#####################################################
    #The output of the elections model is a probability distribution for each district:
    #% Latino, Black, Neither or Overlap effective
    #To compute these, each election set is first weighted (different for Black and Latino)
    #by multiplying a recency weight (W1), "in-group"-minority-preference weight (W2) and
    #a preferred-candidate-confidence weight (W3).
    #If the Black (Latino) preferred candidate wins the election (set) a number of points equal to
    #the set's weight is accrued. The ratio of the accrued points points to the total possible points
    #is the raw Black (Latino)-effectiviness score for the district.

    # After the raw scores are computed, they are adjusted using an "Alignment" score, or a score
    # that measures the share of votes cast for a minority-preferred candidate by the minority group itself.

    # Finally, the Black, Latino, Overlap, and Neither distribution (the values sum to 1)
    # is computed, by feeding the adjusted effectiveness scores through a logit function,
    # and interpolating for the final four values.

    #We need to track several entities in the model, which will be dataframes, whose columns are districts and
    #rows are election sets (or sometimes individual elections)
    #These dataframes each store one of the following: Black (latino) preferred candidates (in the
    #election set's primary), Black (Latino) preferred candidates in runoffs, winners of primary,
    #runoff and general elections, election winners, weights W1, W2 and W3, Alignment scores
    #and final election set weight for Black and Latino voters
    ###########################################################
    #We only need to run model on two ReCom districts that have changed in each step

    dist_changes = list(set(part_assingment.values()))


    elections = data["elections"]
    candidates = data["candidates"]
    elec_data_trunc = data["elec_data_trunc"]
    elec_sets = data["elec_sets"]
    state_gdf = data["state_gdf"]
    primary_elecs = data["primary_elecs"]
    state_prefs = data["black_pref_cands_prim_state"][[0, "Election Set"]]
    black_pref_cands_prim_state = state_prefs.assign(**{str(d): state_prefs[0] for d in dist_changes})
    elec_match_dict = data["elec_match_dict"]
    mean_prec_counts = data["mean_prec_counts"]
    geo_id = data["geo_id"]
    black_weight_state_temp = data["black_weight_state"][[0, "Election Set"]]
    black_weight_state = black_weight_state_temp.assign(**{str(d): black_weight_state_temp[0] for d in dist_changes})
    cand_race_table = data["cand_race_table"]
    elec_set_dict = data["elec_set_dict"]
    logit_params = data["logit_params"]
    partId = data["partId"]

    # print(dist_changes)
    #dictionary to store district-level candidate vote shares
    dist_elec_results = {}
    state_gdf_w_districts = state_gdf.assign(new_dists=state_gdf[partId].map(part_assingment))
    gdf_dists = state_gdf_w_districts.groupby("new_dists").sum()
    index_part_assign = state_gdf_w_districts.new_dists.dropna().astype(int).to_dict()
    # print(index_part_assign)
    for elec in elections:
        cands = candidates[elec].values()
        outcomes = gdf_dists[cands].div(gdf_dists[cands].sum(axis=1), axis=0)
        dist_elec_results[elec] = outcomes.to_dict("index")
    # print(dist_elec_results)
    ##########################################################################################
    #compute winners of each election in each district and store:
    map_winners = pd.DataFrame(columns = dist_changes)
    map_winners["Election"] = elections
    map_winners["Election Set"] = elec_data_trunc["Election Set"]
    map_winners["Election Type"] = elec_data_trunc["Type"]
    for i in dist_changes:
        map_winners[i] = [max(dist_elec_results[elec][i].items(), key=operator.itemgetter(1))[0] for elec in elections]

#########################################################################################
    #If we compute statewide modes: compute alignment/group-control scores for each district #################
    #and final probability distributions
    black_align_prim_state = compute_align_scores(dist_changes, elec_sets, state_gdf, index_part_assign, primary_elecs, \
                                                    black_pref_cands_prim_state, elec_match_dict, \
                                                    mean_prec_counts, geo_id)


    #district probability distribution: statewide
    final_state_prob_dict = compute_final_dist(map_winners, black_pref_cands_prim_state, \
                 black_weight_state, dist_elec_results, dist_changes,
                 cand_race_table, candidates, elec_sets, elec_set_dict,  \
                 black_align_prim_state,  "statewide", logit_params, logit = True, single_map = False)



    final_state_prob = {key:final_state_prob_dict[key] for key in sorted(final_state_prob_dict)}

    primary_races = [elec_set_dict[elec_set]["Primary"] for elec_set in black_pref_cands_prim_state["Election Set"]]
    cand_party_dict = cand_race_table.set_index("Candidates").to_dict()["Party"]
    summary = {}
    for dist in dist_changes:
        d = str(dist)
        # print(black_align_prim_state[d])
        primary_race_share_dict = {primary_race:dist_elec_results[primary_race][dist] for primary_race in primary_races}
        primary_ranking = {primary_race:{key: rank for rank, key in \
                           enumerate(sorted(primary_race_share_dict[primary_race], \
                           key=primary_race_share_dict[primary_race].get, reverse=True), 1)} \
                                            for primary_race in primary_race_share_dict.keys()}

        prefered_candidates = black_pref_cands_prim_state.set_index("Election Set")[d]
        summary[d] = {}
        summary[d]["score"] = final_state_prob[dist]
        summary[d]["electionDetails"] = []
        for i, elect in elec_data_trunc.iterrows():
            if (elect["Type"] == "Primary"):
                elect_set = elect["Election Set"]
                primary = elect["Election"]
                pref_cand = prefered_candidates[elect_set]

                exists_gen = ((elec_data_trunc["Type"] == "General") & (elec_data_trunc["Election Set"] == elect_set)).any()

                if exists_gen:
                    general = elec_data_trunc.query("Type == 'General' and `Election Set` == @elect_set").reset_index().Election[0]
                    gen_cands = {c: cand_party_dict[c] for c in candidates[general].values()}
                    # print(gen_cands)
                    CoC_proxy = [cand for cand, party in gen_cands.items() if party == "D"][0]
                    proxy_perc = dist_elec_results[general][dist][CoC_proxy]
                else:
                    CoC_proxy = ""
                    proxy_perc = ""

                elect_sum = {
                                "name": elect_set,
                                "CoC": pref_cand,
                                "CoC_perc": dist_elec_results[primary][dist][pref_cand],
                                "CoC_place": primary_ranking[primary][pref_cand],
                                "GroupControl": black_align_prim_state.set_index("Election Set")[d][elect_set],
                                "FirstPlace": max(primary_race_share_dict[primary].items(), key=operator.itemgetter(1)),
                                "numCands": len(candidates[primary]),
                                "exists_gen": str(exists_gen),
                                "CoC_proxy": CoC_proxy,
                                "proxy_perc": proxy_perc
                            }
                summary[d]["electionDetails"].append(elect_sum)

    return summary
