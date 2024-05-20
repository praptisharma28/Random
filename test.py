class TestDeviceMonitoring(CreateConnectionsMixin, BaseTestCase):
    """
    Test openwisp_monitoring.device.models.DeviceMonitoring
    """

    def _create_env(self):
        d = self._create_device()
        dm = d.monitoring
        dm.status = 'ok'
        dm.save()
        ping = self._create_object_metric(
            name='ping', key='ping', field_name='reachable', content_object=d
        )
        self._create_alert_settings(
            metric=ping, custom_operator='<', custom_threshold=1, custom_tolerance=0
        )
        load = self._create_object_metric(name='load', content_object=d)
        self._create_alert_settings(
            metric=load, custom_operator='>', custom_threshold=90, custom_tolerance=0
        )
        process_count = self._create_object_metric(
            name='process_count', content_object=d
        )
        self._create_alert_settings(
            metric=process_count,
            custom_operator='>',
            custom_threshold=20,
            custom_tolerance=0,
        )
        return dm, ping, load, process_count

    def test_disabling_critical_check(self):

        Check = load_model('check', 'Check')
        dm, ping, load, process_count = self._create_env()

        ping_check_instance = Check.objects.create(
            name='Ping Check',
            check_type=CHECK_CLASSES[0][0],
            content_object=dm,
            params={},
        )
        dm.update_status('ok')

        self.assertEqual(dm.status, 'ok')
        with catch_signal(health_status_changed) as handler:
            ping_check_instance.is_active = False
            ping_check_instance.save()
        self.assertEqual(handler.call_count, 1)
        call_args = handler.call_args[0]
        self.assertEqual(call_args[0], dm)
        self.assertEqual(call_args[1], 'unknown')
        dm.refresh_from_db()
        self.assertEqual(dm.status, 'unknown')
        dm.update_status('ok')

    def test_saving_active_critical_check(self):

        Check = load_model('check', 'Check')
        dm, ping, load, process_count = self._create_env()

        ping_check_instance = Check.objects.create(
            name='Ping Check',
            check_type=CHECK_CLASSES[0][0],
            content_object=dm,
            params={},
        )
        dm.update_status('ok')

        self.assertEqual(dm.status, 'ok')
        ping_check_instance.is_active = True
        ping_check_instance.save()
        dm.refresh_from_db()
        self.assertEqual(dm.status, 'ok')

    def test_saving_non_critical_check(self):

        Check = load_model('check', 'Check')
        dm, ping, load, process_count = self._create_env()

        self.assertEqual(dm.status, 'ok')
        non_critical_check = Check.objects.create(
            name='Configuration Applied',
            check_type=CHECK_CLASSES[1][0],
            content_object=dm,
            params={},
        )
        non_critical_check.save()
        dm.refresh_from_db()
        self.assertEqual(dm.status, 'ok')

    def test_deleting_critical_check(self):

        Check = load_model('check', 'Check')
        dm, ping, load, process_m = self._create_env()

        ping_check_instance = Check.objects.create(
            name='Ping Check',
            check_type=CHECK_CLASSES[0][0],
            content_object=dm,
            params={},
        )
        dm.update_status('ok')

        dm.update_status('ok')
        ping_check_instance.delete()
        dm.refresh_from_db()
        self.assertEqual(dm.status, 'unknown')
