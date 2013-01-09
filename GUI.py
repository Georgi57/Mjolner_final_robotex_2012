import wx
import tests
import threshold
"""
This a GUI for Team Kondekas programs. This is use just used comfort.
With this you don't have to use consol for running most of the programs.
"""

class MainPage(wx.Panel):
    """
    Page, where the game settings and game start are
    """
    robot = None
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        thsizer = wx.BoxSizer(wx.HORIZONTAL)
        thsizer.Add(wx.StaticText(self, -1, "Manual configuration of thresholds:     "), 0, wx.ALIGN_CENTER, 5)
        button = wx.Button(self,label="Configure")
        button.Bind(wx.EVT_BUTTON, self.check_thresholds)
        thsizer.Add(button, 0, wx.EXPAND, 5)
        sizer.Add(thsizer, 0, wx.EXPAND, 5)


        button = wx.Button(self,label="RUN",size=(120,80))
        button.Bind(wx.EVT_BUTTON, self.run_algorithm)
        sizer.Add(button, 0, wx.ALIGN_CENTER, 5)
        
        self.SetSizer(sizer)

        
        """
        Link to main frame
        """
        self.main = self.GetParent().GetParent().GetParent()

        
        

    def check_thresholds(self,event):
        CV = None
        label = event.GetEventObject().GetLabel()
        if label == "Configure":
            event.GetEventObject().SetLabel("STOP")
            self.CV = threshold.ManualCalibration(self.main.camera)
            self.CV.run()
        else:
            event.GetEventObject().SetLabel("Configure")
            self.CV.stop()
            self.CV = None

    def run_algorithm(self,event):
        label = event.GetEventObject().GetLabel()
        if label == "RUN":
            event.GetEventObject().SetLabel("STOP")
            import main
            self.robot=main.Omnirobot(self.main.debug,self.main.camera,self.main.gate)
            self.robot.run()
        else:
            event.GetEventObject().SetLabel("RUN")
            if self.robot and self.robot.running:
                self.robot.stop()
        
        

class TestPage(wx.Panel):
    
    target = "Ball"
    test = tests.Tests()
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        t = wx.StaticText(self, -1, "TESTS     To stop a running test:   ", (8,8))

        button = wx.Button(self,-1,"STOP all", (220,4))
        button.Bind(wx.EVT_BUTTON, self.stop_all)

        button = wx.Button(self,-1,"Search for",(8,36))
        button.Bind(wx.EVT_BUTTON, self.search_for_target)

        self.radio1 = wx.RadioButton(self, label="Ball",style = wx.RB_GROUP,pos=(120,42))
        self.radio2 = wx.RadioButton(self, label="Blue gate",pos=(175,42))
        self.radio3 = wx.RadioButton(self, label="Yellow gate",pos=(265,42))
        
        self.radio1.Bind(wx.EVT_RADIOBUTTON, self.change_target)
        self.radio2.Bind(wx.EVT_RADIOBUTTON, self.change_target)
        self.radio3.Bind(wx.EVT_RADIOBUTTON, self.change_target)

        button = wx.Button(self,-1,"KICK",(8,88))
        button.Bind(wx.EVT_BUTTON, self.test_kick)

        button = wx.Button(self,-1,"Robot values",(150,88))
        button.Bind(wx.EVT_BUTTON, self.get_values)

        button = wx.Button(self,-1,"test drive",(250,88))
        button.Bind(wx.EVT_BUTTON, self.test_drive)
        
        button = wx.Button(self,-1,"Show camera",(8,124))
        button.Bind(wx.EVT_BUTTON, self.test_camera)
        
        button = wx.Button(self,-1,"Show small camera",(108,124))
        button.Bind(wx.EVT_BUTTON, self.test_small_camera)

        button = wx.Button(self,-1,"Manual control",(8,160))
        button.Bind(wx.EVT_BUTTON, self.manual_control)

        """
        Link to main frame
        """
        self.main = self.GetParent().GetParent().GetParent()

    def search_for_target(self,event):
        if self.test.running:
            print "Something already running"
        else:
            self.test.search_for(self.main.camera,self.target)

    def change_target(self,event):
        label = event.GetEventObject().GetLabel()
        self.target = label

    def stop_all(self,event):
        self.test.running = False

    def test_kick(self,event):
        if self.test.running:
            print "Something already running"
        else:
            self.test.kick()

    def test_camera(self,event):
        if self.test.running:
            print "Something already running"
        else:
            self.test.show_camera(self.main.camera)

    def test_small_camera(self,event):
        if self.test.running:
            print "Something already running"
        else:
            self.test.show_small_camera(self.main.camera)

    def manual_control(self,event):
        if self.test.running:
            print "Something already running"
        else:
            self.test.manual_control(self.main.camera)

    def get_values(self,event):
        if self.test.running:
            print "Something already running"
        else:
            self.test.robot_values()

    def test_drive(self,event):
        if self.test.running:
            print "Something already running"
        else:
            self.test.test_drive()

class MainFrame(wx.Frame):

    debug = False
    camera = 1
    gate = "gye"
    
    def __init__(self):
        wx.Frame.__init__(self, None, title="Team Kondekas. Robotex 2012")
        sizer = wx.BoxSizer(wx.VERTICAL)
        menuSizer = wx.BoxSizer(wx.HORIZONTAL)

        p = wx.Panel(self)
        """
        GUI for variables: DEBUG, CAMERA
        """
        self.debug_checkbox = wx.CheckBox(p, -1, 'DEBUG', (10, 10))
        self.debug_checkbox.SetValue(False)
        wx.EVT_CHECKBOX(self, -1, self.change_debug_value)
        menuSizer.Add(self.debug_checkbox, 1, wx.EXPAND)

        self.debug_checkbox.Bind(wx.EVT_ENTER_WINDOW, self.EnterCheckbox)

        self.camera_combobox = wx.ComboBox(p, choices=["CAMERA 0","CAMERA 1"],style = wx.CB_READONLY)
        self.camera_combobox.Bind(wx.EVT_COMBOBOX, self.camera_select)
        self.camera_combobox.SetStringSelection("CAMERA 1")
        menuSizer.Add(self.camera_combobox, 1, wx.SHAPED|wx.ALIGN_RIGHT)

        

        sizer.Add(menuSizer, 0, wx.ALL, 5)
        """
        Creating a notebook
        """
        # Here we create a panel and a notebook on the panel
        
        self.nb = wx.Notebook(p)

        # create the page windows as children of the notebook
        self.page1 = MainPage(self.nb)
        self.page2 = TestPage(self.nb)

        # add the pages to the notebook with the label to show on the tab
        self.nb.AddPage(self.page1, "Main page")
        self.nb.AddPage(self.page2, "Other tests")

        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        sizer.Add(self.nb, 1, wx.EXPAND)
        p.SetSizer(sizer)

        self.status = self.CreateStatusBar()

        self.SetSize((400,400))
        self.SetMinSize((400,400))

    def change_debug_value(self,event):
        self.debug = self.debug_checkbox.GetValue()

    def camera_select(self,event):
        self.camera = int(self.camera_combobox.GetValue()[-1])

    def EnterCheckbox(self, event):
        self.status.SetStatusText('Turn DEBUG mode on')
        event.Skip()


if __name__ == "__main__":
    app = wx.App()
    MainFrame().Show()
    print "GUI started"
    app.MainLoop()
    
