"""Checks for time boundaries, target rules and the frozen prediction method."""
import copy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import prediction_test as prediction


class PredictionTestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=prediction.load_config()
        cls.tables,cls.results=prediction.load_inputs(cls.config)
        cls.status=prediction.read_status_cache(cls.config,cls.results)
        cls.pairs=prediction.build_pairs(cls.tables,cls.results,cls.status,cls.config)

    def test_prior_rating_ignores_deleted_or_corrupted_current_and_future_data(self):
        for number in [5,10,13,24]:
            expected=prediction.rebuild_prior(self.tables,number,self.config)
            truncated={name:frame[frame.round_number<number].copy() for name,frame in self.tables.items()}
            pd.testing.assert_frame_equal(expected,prediction.rebuild_prior(truncated,number,self.config),check_exact=True)
            altered=copy.deepcopy(self.tables)
            for frame in altered.values():
                mask=frame.round_number>=number
                for column in frame.columns:
                    if column!='round_number':frame.loc[mask,column]='future poison'
            pd.testing.assert_frame_equal(expected,prediction.rebuild_prior(altered,number,self.config),check_exact=True)
            self.assertTrue((expected.source_max_round<number).all())

    def test_current_qualifying_and_results_do_not_enter_prior_rating(self):
        altered=copy.deepcopy(self.tables)
        altered['qualifying'].loc[altered['qualifying'].round_number.eq(13),'combined_gap']='99999'
        pd.testing.assert_frame_equal(prediction.rebuild_prior(self.tables,13,self.config),
                                      prediction.rebuild_prior(altered,13,self.config),check_exact=True)

    def test_swap_is_exact_complement_in_both_directions(self):
        x=np.array([[-1.2,.3],[0,0],[.2,-.1],[.77,.11],[30,-1],[-30,1]])
        beta=np.array([.7,1.3])
        positive=prediction.symmetric_probability(x,beta)
        reverse=prediction.symmetric_probability(-x,beta)
        np.testing.assert_array_equal(positive,1-reverse)
        np.testing.assert_array_equal(reverse,1-positive)
        fit=prediction.fit_logistic(x,[0,1,1,1,1,0],self.config)
        np.testing.assert_array_equal(fit.predict(-x),1-fit.predict(x))

    def test_no_intercept_and_regularized_logistic_optimum(self):
        x=np.array([[-1.],[-.5],[.5],[1.]])
        y=np.array([0,0,1,1])
        fit=prediction.fit_logistic(x,y,self.config)
        self.assertEqual(fit.intercept,0.)
        self.assertEqual(fit.coefficients.shape,(1,))
        self.assertEqual(float(fit.predict([[0.]])[0]),.5)
        gradient=x.T@(fit.predict(x)-y)+fit.coefficients/self.config['logistic']['C']
        self.assertLess(abs(gradient[0]),1e-7)

    def test_points_and_race_win_columns_are_not_read(self):
        real=pd.read_csv
        def guarded(*args,**kwargs):
            self.assertIn('usecols',kwargs)
            self.assertFalse({'points','wins'} & {c.lower() for c in kwargs['usecols']})
            return real(*args,**kwargs)
        with patch.object(prediction.pd,'read_csv',side_effect=guarded):
            prediction.load_inputs(self.config)
            prediction.validate_full_slice(self.tables,self.config)
        poisoned=copy.deepcopy(self.tables)
        for frame in poisoned.values():
            frame['points']='never inspect this'
            frame['wins']='never inspect this'
        pd.testing.assert_frame_equal(prediction.rebuild_prior(self.tables,13,self.config),
                                      prediction.rebuild_prior(poisoned,13,self.config),check_exact=True)

    def test_status_counts_exclusions_and_lapped_finishers(self):
        self.assertEqual(len(self.status),479)
        self.assertTrue(self.status.position_matches_csv.all())
        self.assertEqual(self.status.status.value_counts().to_dict(),
                         {'Finished':330,'Lapped':89,'Retired':51,'Disqualified':6,'Did not start':3})
        counts={target:sum(not prediction.target_reason(row,target,self.config) for row in self.pairs.to_dict('records')) for target in self.config['target_rules']}
        self.assertEqual(counts,{'main_both_finish':185,'all_starters':232,'no_double_retirement':229})
        self.assertEqual(prediction.target_reason(dict(result_present=True,status_a='Lapped',status_b='Finished',valid_positions=True),'main_both_finish',self.config),'')
        path=prediction.path_for(self.config,'outputs','status')
        if path.exists():
            saved=pd.read_csv(path)
            self.assertEqual(saved.status.value_counts().to_dict(),self.status.status.value_counts().to_dict())
            self.assertTrue(saved.position_matches_csv.all())

    def test_bootstrap_repeatable_and_keeps_shared_weekend_draws(self):
        frame=pd.DataFrame([{'round_number':n,'pair_id':f'{n}_{i}','method':method,'outcome':i%2,'probability':p}
                            for n in [13,14,15] for i in range(n-11) for method,p in [('M2',.4),('M3',.4)]])
        first=prediction.weekend_bootstrap(frame,self.config)
        second=prediction.weekend_bootstrap(frame,self.config)
        for metric in prediction.METRICS:
            np.testing.assert_array_equal(first['M2'][metric],second['M2'][metric])
            np.testing.assert_array_equal(first['M2'][metric],first['M3'][metric])
        self.assertEqual(len(first['M2']['brier']),2000)

    def test_tie_credit_and_smoothing(self):
        values=prediction.metric_arrays([0,1,1],[.5,.5,.8],self.config)
        np.testing.assert_array_equal(values['accuracy'],[.5,.5,1.])
        self.assertEqual(prediction.smooth_probability(0,0,self.config),.5)
        self.assertEqual(prediction.smooth_probability(2,3,self.config),.6)
        finite=prediction.metric_arrays([1,0],[0,1],self.config)
        self.assertTrue(np.isfinite(finite['log_loss']).all())
        np.testing.assert_array_equal(finite['brier'],[1,1])

    def test_full_slice_matches_saved_rating_with_rounding_tolerance(self):
        check=prediction.validate_full_slice(self.tables,self.config)
        self.assertEqual(len(check),21)
        self.assertLessEqual(check.absolute_difference.max(),.000500000001)
        np.testing.assert_array_equal(check.combined_rating_rebuilt.round(3),check.combined_rating_saved)

    def test_actual_teammates_and_new_driver_history(self):
        q=self.tables['qualifying']
        self.assertEqual(q[(q.driver=='TSU')&(q.round_number==2)].teammate.iloc[0],'HAD')
        self.assertEqual(q[(q.driver=='TSU')&(q.round_number==3)].teammate.iloc[0],'VER')
        before=prediction.rebuild_prior(self.tables,7,self.config)
        self.assertNotIn('COL',before.driver.tolist())
        ready=prediction.rebuild_prior(self.tables,10,self.config).set_index('driver')
        self.assertEqual(ready.loc['COL','qualifying_valid'],3)

    def test_previous_race_uses_exact_pair_and_main_target_only(self):
        changed=self.pairs[(self.pairs.round_number==3)&(self.pairs.driver_a=='TSU')].iloc[0]
        self.assertTrue(pd.isna(changed.previous_pick))
        self.assertEqual(changed.head_to_head_probability,.5)
        new=self.pairs[(self.pairs.round_number==7)&(self.pairs.driver_a=='COL')].iloc[0]
        self.assertTrue(pd.isna(new.previous_pick))
        self.assertEqual(new.head_to_head_comparisons,0)

    def test_round_counts_and_current_qualifying_exclusions(self):
        features,_=prediction.build_feature_table(self.tables,self.pairs,self.config)
        eligibility=prediction.make_eligibility(self.pairs,features,self.config)
        counts=prediction.count_samples(eligibility,self.config).set_index('target')
        self.assertEqual(counts.loc['main_both_finish','main_rows'],95)
        self.assertEqual(counts.loc['all_starters','main_rows'],113)
        self.assertEqual(counts.loc['no_double_retirement','main_rows'],111)
        missing=set(self.pairs.loc[~self.pairs.valid_qualifying,'pair_id'])
        self.assertEqual(len(missing),7)
        self.assertFalse(eligibility[eligibility.pair_id.isin(missing)].eligible.any())

    def test_training_excludes_same_weekend_and_records_fallback(self):
        features=pd.DataFrame([dict(round_number=n,pair_id=str(n),driver_a='A',driver_b='B',outcome=n%2,
                                   rating_difference=.1,qualifying_advantage=.2,qualifying_pick=1.,grid_pick=1.,
                                   previous_pick=np.nan,head_to_head_probability=.5) for n in range(5,25)])
        eligible=pd.DataFrame([dict(target=t,pair_id=str(n),eligible=True) for t in self.config['target_rules'] for n in range(5,25)])
        preds,coefs=prediction.make_predictions(features,eligible,self.config)
        self.assertTrue((preds.training_max_round<preds.round_number).all())
        self.assertTrue(coefs[coefs.prediction_round<20].fallback_reason.eq('too_few_earlier_training_rows').all())
        self.assertTrue(coefs[coefs.prediction_round>=20].fallback_reason.eq('').all())
        for _,g in preds[preds.round_number<20].groupby(['target','round_number']):
            indexed=g.set_index('method')
            self.assertEqual(indexed.loc['M3','probability'],indexed.loc['qualifying','probability'])

    def test_outputs_protect_previous_runs(self):
        with tempfile.TemporaryDirectory() as temporary:
            first=prediction.new_run_folder(self.config,temporary)
            second=prediction.new_run_folder(self.config,temporary)
            self.assertEqual(first.name,'prediction_001')
            self.assertEqual(second.name,'prediction_002')
            path=first/'example.csv'
            prediction.write_csv(pd.DataFrame({'x':[1]}),path)
            with self.assertRaises(FileExistsError):prediction.write_csv(pd.DataFrame({'x':[2]}),path)


if __name__=='__main__':
    unittest.main()
