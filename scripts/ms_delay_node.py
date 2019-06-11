#!/usr/bin/env python

"""
A node which provides a fixed delay to a topic transmission. It doesn't alter
message contents
"""

import rospy
import sys
import rostopic
import threading
if sys.version_info < (3, 0):
    import Queue as queue
else:
    import queue


class MSDelayNode(object):

    def __init__(self, in_topic, out_topic, ms_delay=1000):
        self.delay = rospy.Duration.from_sec(ms_delay / 1000.0)
        self.publish_queue = queue.Queue(maxsize=0)

        # code borrowed from mongodb_log.py
        try:
            msg_class, real_topic, msg_eval = \
                rostopic.get_topic_class(in_topic, blocking=False)
        except Exception, e:
            print('Topic %s not announced, cannot get type: %s' %
                  (in_topic, e))
            raise

        if real_topic is None:
            raise rostopic.ROSTopicException('topic type was empty, ' +
                                             'probably not announced')

        print('Adding delay of ' + str(self.delay.to_sec()) + 's to: ' +
              real_topic)

        self.publisher = rospy.Publisher(out_topic, msg_class, queue_size=10)
        self.publish_thread = threading.Thread(target=self.publish_loop)
        self.publish_thread.start()
        self.subscriber = rospy.Subscriber(real_topic, msg_class,
                                           callback=self.queue_message)

    def queue_message(self, msg):
        now = rospy.get_rostime()
        then = now + self.delay
        # print('queue', now.to_sec(), then.to_sec())
        self.publish_queue.put((then, msg))

    def publish_loop(self):
        while not rospy.is_shutdown():
            try:
                # block for a 1ms on the queue. This gives us our
                # rough cycle time
                now = rospy.get_rostime()
                pub_time, msg = self.publish_queue.get(timeout=1)
                if now > pub_time:
                    # print('pub', now.to_sec(), pub_time.to_sec())
                    self.publisher.publish(msg)
                else:
                    self.publish_queue.put((pub_time, msg))
            except queue.Empty:
                pass


if __name__ == '__main__':
    rospy.init_node('ms_delay_node')
    args = rospy.myargv(argv=sys.argv)
    if len(args) < 3:
        rospy.logfatal('Run as rosrun ms_topic_delay ms_delay_node.py ' +
                       '<input topic> <output topic>')
        sys.exit(0)

    delay = 1000
    if len(args) > 3:
        delay = int(args[3])

    server = MSDelayNode(args[1], args[2], delay)
    rospy.spin()
