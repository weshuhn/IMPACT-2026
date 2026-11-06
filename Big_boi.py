from dataclasses import dataclass
from datetime import datetime
import matplotlib.pyplot as plt
import math

try:
    import FreeCAD as App
    import Part
    import FreeCADGui as Gui

    doc = App.newDocument("Testing_build")

except ImportError:
    None

@dataclass
class Point:
    x: float
    y: float

@dataclass
class Box:
    top_left: Point
    bottom_right: Point
    height: float = 0
    id: str = None
    @property
    def top_right(self):
        return Point(
            self.bottom_right.x,
            self.top_left.y
        )
    @property
    def bottom_left(self):
        return Point(
            self.top_left.x,
            self.bottom_right.y
        )
    @property
    def center(self):
        return Point(
            (self.top_left.x + self.bottom_right.x) / 2,
            (self.top_left.y + self.bottom_right.y) / 2
        )

@dataclass
class Post(Box):
    ending: str = None  # "block", "paver", or "concrete"


#print(obj.top_left.x)  # 0
#print(deck.top_right.y)    # 96

class Main:
    # a ramp is a ramp without a deck, think about that
    def __init__(self,deck=None,ramp=None,stairs=None):
        self.deck_config=deck
        self.ramp_config=ramp
        self.stairs_config_list=stairs

        if (ramp != None):
            self.deck_ramp=True
            self.ramp_connection_side = ramp["Ramp_connection_side"]
            self.ramp_connection_corner = ramp["Ramp_connection_corner"]  
            self.ramp_connection_offset = ramp["Ramp_connection_offset"]
        else:
            self.ramp_connection_side="GIBER"
            self.deck_ramp=False
        if (stairs != None):
            self.deck_stairs=True
        else:
            self.deck_stairs=False
        print("Deck ramp:", self.deck_ramp)
        print("Deck stairs:", self.deck_stairs)
        # costansts (inches)
        self.frame_lumber_width=1.5
        self.frame_lumber_height=5.5
        self.max_joist_spacing = 24 

        self.decking_lumber_width=5.5
        self.decking_lumber_height=1

        self.post_width=3.5
        self.post_height_above_frame=36

        # deck block height 7.5 in
        # deck block post set height = 6 in
        self.deckblock_height=7.5
        self.deckblock_post_offset=1.5

        self.paver_height=1.5
        # cleats
        self.min_cleat_length=4

        self.concrete_depth=12

        self.ramp_width=48

        self.max_span=96

        if self.deck_config != None:
            self.design_deck(self.deck_config,self.ramp_config,self.stairs_config_list)

    def design_deck(self,config,ramp_config_input=None,stairs_config_input=None):
        self.deck_length = int(config["Length"])
        self.deck_width = int(config["Width"])
        self.deck_height_to_door = int(config["height_to_door"])
        self.pavers_house = config["pavers_house"]
        self.no_handrail_side = config["No_handrail_side"]
        self.deck_decking_orientation = config["decking_orientation"]

        #
        # Frame
        #
        # Left and right sides full length
        if (self.deck_length>self.deck_width or self.deck_width == self.deck_length):
            left_frame=Box(Point(0, 0),Point(self.frame_lumber_width, -self.deck_length),self.frame_lumber_height,"Frame")
            right_frame=Box(Point(self.deck_width-self.frame_lumber_width, 0),Point(self.deck_width, -self.deck_length),self.frame_lumber_height,"Frame")
            # 3 inch short
            back_frame=Box(Point(self.frame_lumber_width, 0),Point(self.deck_width-self.frame_lumber_width, -self.frame_lumber_width),self.frame_lumber_height,"Frame") 
            front_frame=Box(Point(self.frame_lumber_width, -self.deck_length+self.frame_lumber_width),Point(self.deck_width-self.frame_lumber_width, -self.deck_length),self.frame_lumber_height,"Frame")
        else:
            back_frame=Box(Point(0, 0),Point(self.deck_width, -self.frame_lumber_width),self.frame_lumber_height,"Frame")
            front_frame=Box(Point(0, -self.deck_length+self.frame_lumber_width),Point(self.deck_width, -self.deck_length),self.frame_lumber_height,"Frame")
            # 3 inch short
            left_frame=Box(Point(0, -self.frame_lumber_width),Point(self.frame_lumber_width, -self.deck_length+self.frame_lumber_width),self.frame_lumber_height,"Frame")
            right_frame=Box(Point(self.deck_width-self.frame_lumber_width, -self.frame_lumber_width),Point(self.deck_width, -self.deck_length+self.frame_lumber_width),self.frame_lumber_height,"Frame")

        frame=[left_frame,right_frame,back_frame,front_frame]

        
        #
        # joists
        #
        joists = []
        if self.deck_decking_orientation == "Width":
            interior_width = self.deck_width - (2 * self.frame_lumber_width)
            num_spaces = math.ceil(interior_width / self.max_joist_spacing)
            spacing = interior_width / num_spaces
            for i in range(1, num_spaces):
                x = self.frame_lumber_width + (i * spacing)
                joists.append(Box(Point(x - self.frame_lumber_width/2, -self.frame_lumber_width),Point(x + self.frame_lumber_width/2,-self.deck_length+self.frame_lumber_width),self.frame_lumber_height,"Joist"))
        else:
            interior_length = self.deck_length - (2 * self.frame_lumber_width)
            num_spaces = math.ceil(
                interior_length / self.max_joist_spacing
            )
            spacing = interior_length / num_spaces
            for i in range(1, num_spaces):
                y = -(self.frame_lumber_width +(i * spacing))
                joists.append(Box(Point(self.frame_lumber_width, y - self.frame_lumber_width/2),Point(self.deck_width-self.frame_lumber_width,y + self.frame_lumber_width/2),self.frame_lumber_height,"Joist"))

        #
        #  Post
        #

        # 4 corners
        #self.deck_height_to_door + self.post_height_above_frame - self.pavers_house
        #  self.deckblock_height
        self.cleatable_dist=self.deck_height_to_door-self.frame_lumber_height
        if ((self.cleatable_dist-self.deckblock_height) > self.min_cleat_length):
            # ending posts is a block
            ending="block"
            post_height=(self.cleatable_dist-(self.deckblock_height-self.deckblock_post_offset))+self.frame_lumber_height+self.post_height_above_frame

        elif ((self.cleatable_dist-self.paver_height) < self.min_cleat_length):
            # ending is a paver
            ending="paver"
            post_height=(self.cleatable_dist-self.paver_height)+self.frame_lumber_height+self.post_height_above_frame
        else:
            # ending is concrete
            ending="concrete"
            post_height=(self.cleatable_dist)+self.frame_lumber_height+self.post_height_above_frame+self.concrete_depth

        bottom_left_post=Post(Point(self.frame_lumber_width, -self.deck_length+self.frame_lumber_width),Point(self.post_width+self.frame_lumber_width, -self.deck_length+self.frame_lumber_width+self.post_width),post_height,"Post",ending)
        bottom_right_post=Post(Point(self.deck_width-self.frame_lumber_width-self.post_width, -self.deck_length+self.frame_lumber_width),Point(self.deck_width-self.frame_lumber_width, -self.deck_length+self.frame_lumber_width+self.post_width),post_height,"Post",ending)
        
        if (self.pavers_house == True):
            if ((self.cleatable_dist-self.paver_height) < self.min_cleat_length):
                # ending is a paver
                ending="paver"
                post_height=(self.cleatable_dist-self.paver_height)+self.frame_lumber_height+self.post_height_above_frame
            else:
                # ending is concrete
                ending="concrete"
                post_height=(self.cleatable_dist)+self.frame_lumber_height+self.post_height_above_frame+self.concrete_depth
            top_left_post=Post(Point(self.frame_lumber_width, -self.frame_lumber_width),Point(self.post_width+self.frame_lumber_width, -self.frame_lumber_width-self.post_width),post_height,"Post",ending)
            top_right_post=Post(Point(self.deck_width-self.frame_lumber_width-self.post_width, -self.frame_lumber_width),Point(self.deck_width-self.frame_lumber_width, -self.frame_lumber_width-self.post_width),post_height,"Post",ending)
        else:
            top_left_post=Post(Point(self.frame_lumber_width, -self.frame_lumber_width),Point(self.post_width+self.frame_lumber_width, -self.frame_lumber_width-self.post_width),post_height,"Post",ending)
            top_right_post=Post(Point(self.deck_width-self.frame_lumber_width-self.post_width, -self.frame_lumber_width),Point(self.deck_width-self.frame_lumber_width, -self.frame_lumber_width-self.post_width),post_height,"Post",ending)

        
        # If Ramp
        extra_post=[]   

        if self.deck_ramp:
            if self.ramp_connection_side == "Back":
                top_left_post = Post(
                    Point(self.frame_lumber_width, self.post_width),
                    Point(self.post_width + self.frame_lumber_width, 0),
                    post_height,
                    "Post",
                    ending,
                )
                top_right_post = Post(
                    Point(
                        self.deck_width - self.frame_lumber_width - self.post_width,
                        self.post_width,
                    ),
                    Point(self.deck_width - self.frame_lumber_width, 0),
                    post_height,
                    "Post",
                    ending,
                )

                if self.ramp_connection_offset == 0:
                    if self.ramp_connection_corner == "Back_Right":
                        ramp_post1 = Post(
                            Point(
                                top_right_post.top_left.x - self.ramp_width,
                                self.post_width,
                            ),
                            Point(
                                top_right_post.top_left.x - self.ramp_width + self.post_width,
                                0,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Back_Left
                        ramp_post1 = Post(
                            Point(
                                top_left_post.bottom_right.x + self.ramp_width,
                                self.post_width,
                            ),
                            Point(
                                top_left_post.bottom_right.x
                                + self.ramp_width
                                + self.post_width,
                                0,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.append(ramp_post1)

                else:
                    if self.ramp_connection_corner == "Back_Left":
                        ramp_post1 = Post(
                            Point(
                                self.ramp_connection_offset - self.post_width,
                                self.post_width,
                            ),
                            Point(self.ramp_connection_offset, 0),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(
                                self.ramp_connection_offset
                                - self.post_width
                                + self.ramp_width,
                                self.post_width,
                            ),
                            Point(
                                self.ramp_connection_offset + self.ramp_width,
                                0,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Back_Right
                        ramp_post1 = Post(
                            Point(
                                self.deck_width - self.ramp_connection_offset,
                                self.post_width,
                            ),
                            Point(
                                self.deck_width
                                - self.ramp_connection_offset
                                + self.post_width,
                                0,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(
                                self.deck_width
                                - self.ramp_connection_offset
                                - self.ramp_width,
                                self.post_width,
                            ),
                            Point(
                                self.deck_width
                                - self.ramp_connection_offset
                                - self.ramp_width
                                + self.post_width,
                                0,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.extend((ramp_post1, ramp_post2))


            elif self.ramp_connection_side == "Front":
                front_y = -self.deck_length
                front_outer_y = -(self.deck_length + self.post_width)

                bottom_left_post = Post(
                    Point(self.frame_lumber_width, front_y),
                    Point(
                        self.post_width + self.frame_lumber_width,
                        front_outer_y,
                    ),
                    post_height,
                    "Post",
                    ending,
                )
                bottom_right_post = Post(
                    Point(
                        self.deck_width
                        - self.frame_lumber_width
                        - self.post_width,
                        front_y,
                    ),
                    Point(
                        self.deck_width - self.frame_lumber_width,
                        front_outer_y,
                    ),
                    post_height,
                    "Post",
                    ending,
                )

                if self.ramp_connection_offset == 0:
                    if self.ramp_connection_corner == "Front_Right":
                        ramp_post1 = Post(
                            Point(
                                bottom_right_post.top_left.x - self.ramp_width,
                                front_y,
                            ),
                            Point(
                                bottom_right_post.top_left.x
                                - self.ramp_width
                                + self.post_width,
                                front_outer_y,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Front_Left
                        ramp_post1 = Post(
                            Point(
                                bottom_left_post.bottom_right.x + self.ramp_width,
                                front_y,
                            ),
                            Point(
                                bottom_left_post.bottom_right.x
                                + self.ramp_width
                                + self.post_width,
                                front_outer_y,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.append(ramp_post1)

                else:
                    if self.ramp_connection_corner == "Front_Left":
                        ramp_post1 = Post(
                            Point(
                                self.ramp_connection_offset - self.post_width,
                                front_y,
                            ),
                            Point(
                                self.ramp_connection_offset,
                                front_outer_y,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(
                                self.ramp_connection_offset
                                - self.post_width
                                + self.ramp_width,
                                front_y,
                            ),
                            Point(
                                self.ramp_connection_offset + self.ramp_width,
                                front_outer_y,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Front_Right
                        ramp_post1 = Post(
                            Point(
                                self.deck_width - self.ramp_connection_offset,
                                front_y,
                            ),
                            Point(
                                self.deck_width
                                - self.ramp_connection_offset
                                + self.post_width,
                                front_outer_y,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(
                                self.deck_width
                                - self.ramp_connection_offset
                                - self.ramp_width,
                                front_y,
                            ),
                            Point(
                                self.deck_width
                                - self.ramp_connection_offset
                                - self.ramp_width
                                + self.post_width,
                                front_outer_y,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.extend((ramp_post1, ramp_post2))


            elif self.ramp_connection_side == "Left":
                left_x = -self.post_width
                left_inner_x = 0

                top_left_post = Post(
                    Point(left_x, -self.frame_lumber_width),
                    Point(
                        left_inner_x,
                        -(self.post_width + self.frame_lumber_width),
                    ),
                    post_height,
                    "Post",
                    ending,
                )
                bottom_left_post = Post(
                    Point(
                        left_x,
                        -(self.deck_length - self.post_width - self.frame_lumber_width),
                    ),
                    Point(
                        left_inner_x,
                        -(self.deck_length - self.frame_lumber_width),
                    ),
                    post_height,
                    "Post",
                    ending,
                )

                if self.ramp_connection_offset == 0:
                    if self.ramp_connection_corner == "Left_Front":
                        ramp_post1 = Post(
                            Point(
                                left_x,
                                top_left_post.bottom_right.y - self.ramp_width,
                            ),
                            Point(
                                left_inner_x,
                                top_left_post.bottom_right.y
                                - self.ramp_width
                                - self.post_width,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Left_Back
                        ramp_post1 = Post(
                            Point(
                                left_x,
                                bottom_left_post.top_left.y + self.ramp_width,
                            ),
                            Point(
                                left_inner_x,
                                bottom_left_post.top_left.y
                                + self.ramp_width
                                + self.post_width,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.append(ramp_post1)

                else:
                    if self.ramp_connection_corner == "Left_Back":
                        # Offset is measured from the back edge toward the front.
                        first_y = -self.ramp_connection_offset + self.post_width
                        second_y = first_y - self.ramp_width

                        ramp_post1 = Post(
                            Point(left_x, first_y),
                            Point(left_inner_x, first_y - self.post_width),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(left_x, second_y),
                            Point(left_inner_x, second_y - self.post_width),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Left_Front
                        # Offset is measured from the front edge toward the back.
                        first_bottom_y = -(
                            self.deck_length - self.ramp_connection_offset + self.post_width
                        )
                        second_bottom_y = first_bottom_y + self.ramp_width

                        ramp_post1 = Post(
                            Point(left_x, first_bottom_y + self.post_width),
                            Point(left_inner_x, first_bottom_y),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(left_x, second_bottom_y + self.post_width),
                            Point(left_inner_x, second_bottom_y),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.extend((ramp_post1, ramp_post2))


            elif self.ramp_connection_side == "Right":
                right_x = self.deck_width
                right_outer_x = self.deck_width + self.post_width

                top_right_post = Post(
                    Point(right_x, -self.frame_lumber_width),
                    Point(
                        right_outer_x,
                        -(self.post_width + self.frame_lumber_width),
                    ),
                    post_height,
                    "Post",
                    ending,
                )
                bottom_right_post = Post(
                    Point(
                        right_x,
                        -(self.deck_length - self.post_width - self.frame_lumber_width),
                    ),
                    Point(
                        right_outer_x,
                        -(self.deck_length - self.frame_lumber_width),
                    ),
                    post_height,
                    "Post",
                    ending,
                )

                if self.ramp_connection_offset == 0:
                    if self.ramp_connection_corner == "Right_Front":
                        ramp_post1 = Post(
                            Point(
                                right_x,
                                top_right_post.bottom_right.y - self.ramp_width,
                            ),
                            Point(
                                right_outer_x,
                                top_right_post.bottom_right.y
                                - self.ramp_width
                                - self.post_width,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Right_Back
                        ramp_post1 = Post(
                            Point(
                                right_x,
                                bottom_right_post.top_left.y + self.ramp_width,
                            ),
                            Point(
                                right_outer_x,
                                bottom_right_post.top_left.y
                                + self.ramp_width
                                + self.post_width,
                            ),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.append(ramp_post1)

                else:
                    if self.ramp_connection_corner == "Right_Back":
                        # Offset is measured from the back edge toward the front.
                        first_y = -self.ramp_connection_offset + self.post_width
                        second_y = first_y - self.ramp_width

                        ramp_post1 = Post(
                            Point(right_x, first_y),
                            Point(right_outer_x, first_y - self.post_width),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(right_x, second_y),
                            Point(right_outer_x, second_y - self.post_width),
                            post_height,
                            "Post",
                            ending,
                        )
                    else:  # Right_Front
                        # Offset is measured from the front edge toward the back.
                        first_bottom_y = -(
                            self.deck_length - self.ramp_connection_offset + self.post_width
                        )
                        second_bottom_y = first_bottom_y + self.ramp_width

                        ramp_post1 = Post(
                            Point(right_x, first_bottom_y + self.post_width),
                            Point(right_outer_x, first_bottom_y),
                            post_height,
                            "Post",
                            ending,
                        )
                        ramp_post2 = Post(
                            Point(right_x, second_bottom_y + self.post_width),
                            Point(right_outer_x, second_bottom_y),
                            post_height,
                            "Post",
                            ending,
                        )

                    extra_post.extend((ramp_post1, ramp_post2))

            else:
                print("Error: Ramp connection side not recognized")

        


        posts=[top_left_post,top_right_post,bottom_left_post,bottom_right_post]
        
        # Stairs posts
        # Stairs posts
        stair_posts = []

        if self.deck_stairs:
            for stair_name, stair in self.stairs_config_list.items():
                stair_width = stair["Stair_width"]
                stair_connection_side = stair["Stair_connection_side"]
                stair_connection_corner = stair["Stair_connection_corner"]
                stair_connection_offset = stair["Stair_connection_offset"]

                # Stair posts go outside when the stairs share a side with the ramp.
                # Otherwise, stair posts go inside the deck frame.
                place_outside_frame = (
                    self.ramp_connection_side == stair_connection_side
                )

                if stair_connection_side == "Back":
                    if place_outside_frame:
                        post_top_y = self.post_width
                        post_bottom_y = 0
                    else:
                        post_top_y = -self.frame_lumber_width
                        post_bottom_y = -(self.post_width+self.frame_lumber_width)

                    if stair_connection_corner == "Back_Left":
                        if stair_connection_offset == 0:
                            # Reuse the existing back-left corner post.
                            # Only create the post at the far side of the stairs.
                            post_x = (
                                self.frame_lumber_width
                                + self.post_width
                                + stair_width
                            )

                            stair_post1 = Post(
                                Point(post_x, post_top_y),
                                Point(
                                    post_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_x = (
                                stair_connection_offset - self.post_width
                            )
                            second_x = first_x + stair_width

                            stair_post1 = Post(
                                Point(first_x, post_top_y),
                                Point(
                                    first_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(second_x, post_top_y),
                                Point(
                                    second_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    elif stair_connection_corner == "Back_Right":
                        if stair_connection_offset == 0:
                            # Reuse the existing back-right corner post.
                            # Only create the post at the far side of the stairs.
                            post_x = (
                                self.deck_width
                                - self.frame_lumber_width
                                - self.post_width
                                - stair_width
                            )

                            stair_post1 = Post(
                                Point(post_x, post_top_y),
                                Point(
                                    post_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_x = (
                                self.deck_width
                                - stair_connection_offset
                            )
                            second_x = first_x - stair_width

                            stair_post1 = Post(
                                Point(first_x, post_top_y),
                                Point(
                                    first_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(second_x, post_top_y),
                                Point(
                                    second_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    else:
                        print(
                            "Error: Back stair corner not recognized:",
                            stair_connection_corner,
                        )


                elif stair_connection_side == "Front":
                    if place_outside_frame:
                        post_top_y = -self.deck_length
                        post_bottom_y = -(
                            self.deck_length + self.post_width
                        )
                    else:
                        post_top_y = -(
                            self.deck_length - self.post_width-self.frame_lumber_width
                        )
                        post_bottom_y = -self.deck_length+self.frame_lumber_width

                    if stair_connection_corner == "Front_Left":
                        if stair_connection_offset == 0:
                            # Reuse the existing front-left corner post.
                            post_x = (
                                self.frame_lumber_width
                                + self.post_width
                                + stair_width
                            )

                            stair_post1 = Post(
                                Point(post_x, post_top_y),
                                Point(
                                    post_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_x = (
                                stair_connection_offset - self.post_width
                            )
                            second_x = first_x + stair_width

                            stair_post1 = Post(
                                Point(first_x, post_top_y),
                                Point(
                                    first_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(second_x, post_top_y),
                                Point(
                                    second_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    elif stair_connection_corner == "Front_Right":
                        if stair_connection_offset == 0:
                            # Reuse the existing front-right corner post.
                            post_x = (
                                self.deck_width
                                - self.frame_lumber_width
                                - self.post_width
                                - stair_width
                            )

                            stair_post1 = Post(
                                Point(post_x, post_top_y),
                                Point(
                                    post_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_x = (
                                self.deck_width
                                - stair_connection_offset
                            )
                            second_x = first_x - stair_width

                            stair_post1 = Post(
                                Point(first_x, post_top_y),
                                Point(
                                    first_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(second_x, post_top_y),
                                Point(
                                    second_x + self.post_width,
                                    post_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    else:
                        print(
                            "Error: Front stair corner not recognized:",
                            stair_connection_corner,
                        )


                elif stair_connection_side == "Left":
                    if place_outside_frame:
                        post_left_x = -(self.post_width+self.frame_lumber_width)
                        post_right_x = self.frame_lumber_width
                    else:
                        post_left_x = self.frame_lumber_width
                        post_right_x = self.post_width+self.frame_lumber_width

                    if stair_connection_corner == "Left_Back":
                        if stair_connection_offset == 0:
                            # Reuse the existing left-back corner post.
                            post_top_y = -(
                                self.frame_lumber_width
                                + self.post_width
                                + stair_width
                            )

                            stair_post1 = Post(
                                Point(post_left_x, post_top_y),
                                Point(
                                    post_right_x,
                                    post_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_top_y = (
                                -stair_connection_offset
                                + self.post_width
                            )
                            second_top_y = first_top_y - stair_width

                            stair_post1 = Post(
                                Point(post_left_x, first_top_y),
                                Point(
                                    post_right_x,
                                    first_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(post_left_x, second_top_y),
                                Point(
                                    post_right_x,
                                    second_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    elif stair_connection_corner == "Left_Front":
                        if stair_connection_offset == 0:
                            # Reuse the existing left-front corner post.
                            post_top_y = -(
                                self.deck_length
                                - self.frame_lumber_width
                                - self.post_width
                                - stair_width
                            )

                            stair_post1 = Post(
                                Point(post_left_x, post_top_y),
                                Point(
                                    post_right_x,
                                    post_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_bottom_y = -(
                                self.deck_length
                                - stair_connection_offset
                                + self.post_width
                            )
                            first_top_y = (
                                first_bottom_y + self.post_width
                            )
                            second_top_y = first_top_y + stair_width

                            stair_post1 = Post(
                                Point(post_left_x, first_top_y),
                                Point(
                                    post_right_x,
                                    first_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(post_left_x, second_top_y),
                                Point(
                                    post_right_x,
                                    second_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    else:
                        print(
                            "Error: Left stair corner not recognized:",
                            stair_connection_corner,
                        )


                elif stair_connection_side == "Right":
                    if place_outside_frame:
                        post_left_x = self.deck_width  - self.post_width 
                        post_right_x = (
                            self.deck_width + self.post_width - self.frame_lumber_width
                        )
                    else:
                        post_left_x = (
                            self.deck_width - self.post_width - self.frame_lumber_width
                        )
                        post_right_x = self.deck_width - self.frame_lumber_width

                    if stair_connection_corner == "Right_Back":
                        if stair_connection_offset == 0:
                            # Reuse the existing right-back corner post.
                            post_top_y = -(
                                self.frame_lumber_width
                                + self.post_width
                                + stair_width
                            )

                            stair_post1 = Post(
                                Point(post_left_x, post_top_y),
                                Point(
                                    post_right_x,
                                    post_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_top_y = (
                                -stair_connection_offset
                                + self.post_width
                            )
                            second_top_y = first_top_y - stair_width

                            stair_post1 = Post(
                                Point(post_left_x, first_top_y),
                                Point(
                                    post_right_x,
                                    first_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(post_left_x, second_top_y),
                                Point(
                                    post_right_x,
                                    second_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    elif stair_connection_corner == "Right_Front":
                        if stair_connection_offset == 0:
                            # Reuse the existing right-front corner post.
                            post_top_y = -(
                                self.deck_length
                                - self.frame_lumber_width
                                - self.post_width
                                - stair_width
                            )

                            stair_post1 = Post(
                                Point(post_left_x, post_top_y),
                                Point(
                                    post_right_x,
                                    post_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.append(stair_post1)

                        else:
                            first_bottom_y = -(
                                self.deck_length
                                - stair_connection_offset
                                + self.post_width
                            )
                            first_top_y = (
                                first_bottom_y + self.post_width
                            )
                            second_top_y = first_top_y + stair_width

                            stair_post1 = Post(
                                Point(post_left_x, first_top_y),
                                Point(
                                    post_right_x,
                                    first_bottom_y,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_post2 = Post(
                                Point(post_left_x, second_top_y),
                                Point(
                                    post_right_x,
                                    second_top_y - self.post_width,
                                ),
                                post_height,
                                "Post",
                                ending,
                            )

                            stair_posts.extend((stair_post1, stair_post2))

                    else:
                        print(
                            "Error: Right stair corner not recognized:",
                            stair_connection_corner,
                        )

                else:
                    print(
                        "Error: Stair connection side not recognized:",
                        stair_connection_side,
                    )

            extra_post.extend(stair_posts)


        # 12 or 16ft supports or BEAM
        beam_support_pairs = []


        posts.extend(extra_post)

        even_more_extra_posts = []
        beam_boxes=[]

        left_posts=[]
        right_posts=[]
        back_posts=[]
        front_posts=[]
        for post in posts:
            post_center_x = post.center.x
            post_center_y = post.center.y

            if post_center_x <= self.post_width+self.frame_lumber_width:
                left_posts.append(post)

            if post_center_x >= self.deck_width - self.post_width-self.frame_lumber_width:
                right_posts.append(post)

            if post_center_y >= -self.post_width+self.frame_lumber_width:
                front_posts.append(post)

            if post_center_y <= -(self.deck_length - self.post_width-self.frame_lumber_width):
                back_posts.append(post)

        front_posts.sort(key=lambda post: post.center.x)
        back_posts.sort(key=lambda post: post.center.x)
        left_posts.sort(key=lambda post: post.center.y, reverse=True)
        right_posts.sort(key=lambda post: post.center.y, reverse=True)

        if(self.deck_width > self.max_span):
            # need support
            if (self.deck_width >= 192): # 16 ft check
                # support needed at 8ft
                
                # check Back
                back_support_exists = False
                front_support_exists = False
                for post in back_posts:
                    post_center_x = post.center.x
                    post_center_y = post.center.y

                    if abs(post_center_x - self.max_span) < 0.1:
                        back_support_exists = True
                        break

                for post in front_posts:
                    post_center_x = post.center.x
                    post_center_y = post.center.y

                    if abs(post_center_x - self.max_span) < 0.1:
                        front_support_exists = True
                        break

                if (front_support_exists == False):
                    front_support_post = Post(
                        Point(self.max_span - (self.post_width/2),front_posts[0].top_left.y),
                        Point(self.max_span + (self.post_width/2),front_posts[0].bottom_right.y),0,"post"
                        )
                    even_more_extra_posts.append(front_support_post)

                if (back_support_exists == False):
                    back_support_post = Post(
                        Point(self.max_span - (self.post_width/2),back_posts[0].top_left.y),
                        Point(self.max_span + (self.post_width/2),back_posts[0].bottom_right.y),0,"post"
                    )
                    even_more_extra_posts.append(back_support_post)
                if (self.deck_decking_orientation == "Length"):
                    # big daddy beam
                    pass
                    left_beam=Box(
                        Point(front_support_post.top_left.x-self.frame_lumber_width, front_support_post.top_left.y),
                        Point(back_support_post.bottom_right.x-self.post_width, back_support_post.bottom_right.y-self.post_width)
                    )
                    right_beam=Box(
                        Point(front_support_post.top_left.x+self.frame_lumber_width+self.post_width, front_support_post.top_left.y),
                        Point(back_support_post.bottom_right.x, back_support_post.bottom_right.y-self.post_width)
                    )
                    beam_boxes.append(left_beam)
                    beam_boxes.append(right_beam)

                    middle_support_post = Post(
                        Point(front_support_post.top_left.x, (front_support_post.top_left.y+back_support_post.bottom_right.y)/2-(self.post_width/2)),
                        Point(front_support_post.top_left.x+self.post_width, (front_support_post.top_left.y+back_support_post.bottom_right.y)/2+(self.post_width/2)),0,"beam_post"
                    )
                    even_more_extra_posts.append(middle_support_post)
            else:
                last_post_x=0
                for post in back_posts:
                    post_center_x = post.center.x
                    post_center_y = post.center.y

                    if abs(last_post_x - post_center_x) > self.max_span:
                        # place post in middle
                        back_support_post = Post(
                            Point((last_post_x + post_center_x) / 2 - (self.post_width/2), post.top_left.y),
                            Point((last_post_x + post_center_x) / 2 + (self.post_width/2), post.bottom_right.y),0,"post"
                        )
                        even_more_extra_posts.append(back_support_post)

                    last_post_x = post_center_x

                last_post_x=0
                for post in front_posts:
                    post_center_x = post.center.x
                    post_center_y = post.center.y

                    if abs(last_post_x - post_center_x) > self.max_span:
                        # place post in middle
                        print("Placing post in the middle "+str(last_post_x - post_center_x))
                        front_support_post = Post(
                            Point((last_post_x + post_center_x) / 2 - (self.post_width/2), post.top_left.y),
                            Point((last_post_x + post_center_x) / 2 + (self.post_width/2), post.bottom_right.y),0,"post"
                        )
                        even_more_extra_posts.append(front_support_post)

                    last_post_x = post_center_x

                if (self.deck_decking_orientation == "Length"):
                    # BEAM
                    pass

                
                    

                


        posts.extend(even_more_extra_posts)
        frame.extend(beam_boxes)
                
                    
        # Beam

        posts.extend(extra_post)

        # changes to joist from posts


        # hand rails

        # compute all and compare changes

        """
        for i in range(len(frame)):
            self.make_block(frame[i],frame[i].height,frame[i].id)

        for i in range(len(joists)):
            self.make_block(joists[i],joists[i].height,joists[i].id)
        """
        frame.extend(joists)
        frame.extend(posts)
        self.draw_parts(frame)
        print(frame)
        
    def make_connection(self,box1,box2,given_offsetX=0,given_offsetY=0,given_offsetZ=0):

        self.make_block(box1,box1.height,box1.id)
        self.make_block(box2,box2.height,box2.id)

        left1   = box1.top_left.x
        top1  = box1.top_left.y
        right1    = box1.bottom_right.x
        bottom1 = box1.bottom_right.y

        left2   = box2.top_left.x
        top2 = box2.top_left.y
        right2    = box2.bottom_right.x
        bottom2 = box2.bottom_right.y

        middle_length_1=(top1-bottom1)/2
        print(
        f"box1: left={left1}, right={right1}, top={top1}, bottom={bottom1}\n"
        f"box2: left={left2}, right={right2}, top={top2}, bottom={bottom2}"
        )
        # Check connecting sides
        if (left1==right2):
            None
        elif (right1==left2):
            print("Connecting right to left")
            box1_face="Face4"
            box2_face="Face2"

            Xoffset= top2-middle_length_1 #might not be X lol
            print(middle_length_1,Xoffset)

            


    def make_block(self, box, height, id, is_deck_board=False):

        x_min = min(box.top_left.x, box.bottom_right.x)
        y_min = min(box.top_left.y, box.bottom_right.y)

        width = abs(box.bottom_right.x - box.top_left.x)
        depth = abs(box.bottom_right.y - box.top_left.y)

        block = Part.makeBox(
            width,
            depth,
            height
        )

        block.translate(
            FreeCAD.Vector(
                x_min,
                y_min,
                0
            )
        )

        group = doc.getObject(id)

        if group is None:
            group = doc.addObject(
                "App::DocumentObjectGroup",
                id
            )

        obj = doc.addObject(
            "Part::Feature",
            f"{id}_Block"
        )

        obj.Shape = block

        group.addObject(obj)

        doc.recompute()

        return obj

    def draw_parts(self,parts):
        fig, ax = plt.subplots()

        for part in parts:
            # Parse points from Box
            x1 = part.top_left.x
            y1 = part.top_left.y
            x2 = part.bottom_right.x
            y2 = part.bottom_right.y

            # Draw rectangle
            xs = [x1, x2, x2, x1, x1]
            ys = [y1, y1, y2, y2, y1]

            ax.plot(xs, ys)

        ax.set_aspect("equal")
        ax.grid(True)
        plt.show()    


#
# Testing input
#

##
## RAMP OFFSET VALUE IS THE STARTIONG CORNETR OF THE RAMP NOT THE POST
##

deck_test={"Length":"144",
      "Width": "96",
      "height_to_door": "36",
      "pavers_house": True,
      "No_handrail_side": "Left",
      "decking_orientation": "Length"
      }

Ramp={
        "Description": "8ft,8ft,LAN,8ft",
        "Ramp_connection_side": "Back",
        "Ramp_connection_corner": "Back_Right",
        "Ramp_connection_offset": 10
    }

stairs = {
    "Stair1": {
        "Stair_width": 36,
        "Stair_connection_side": "Front",
        "Stair_connection_corner": "Front_Left",
        "Stair_connection_offset": 0
    },
    "Stair2": {
            "Stair_width": 36,
            "Stair_connection_side": "Right",
            "Stair_connection_corner": "Right_Front",
            "Stair_connection_offset": 10
        },
}

deck={"Length":"96",
      "Width": "144",
      "height_to_door": "12",
      "pavers_house": True,
      "No_handrail_side": "Left",
      "decking_orientation": "Length"
      }

deck2={"Length":"192",
      "Width": "192",
      "height_to_door": "48",
      "pavers_house": True,
     "No_handrail_side": "Left",
      "decking_orientation": "Length"
      }

deck_test_set=[]
deck_test_set.append(deck_test)

valid_corners = {
    "Back": ["Back_Left", "Back_Right"],
    "Front": ["Front_Left", "Front_Right"],
    "Left": ["Left_Back", "Left_Front"],
    "Right": ["Right_Back", "Right_Front"]
}
"""
for side, corners in valid_corners.items():
    for corner in corners:
        test_ramp = Ramp.copy()
        test_ramp["Ramp_connection_side"] = side
        test_ramp["Ramp_connection_corner"] = corner

        print(f"Testing: {side=} {corner=}")
        Main(deck_test,Ramp)
"""
#main=Main(deck_test,None,stairs)

main=Main(deck,Ramp)

main=Main(deck2,Ramp)

#timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
#file_path = (
#    rf"C:\Users\weshu\OneDrive\Desktop\IMPACT 2026"
#    rf"\Deck_{timestamp}.FCStd"
#)

#doc.saveAs(file_path)
#subprocess.Popen([
#    r"C:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe",
#    file_path
#])

#se=input("Press Enter to exit...")












"""
deck={"Length":"96",
      "Width": "144",
      "decking_orientation": "Width"
      }

main=Main(deck_test)



overall_design = {
    "Deck": {
        "length": 96,
        "width": 96,
        "decking_orientation": "Width"
    },
    "Ramp": {
        "Description": "8ft,8ft,LAN,8ft",
        "Ramp_connection_side": "Left",
        "Ramp_connection_corner": "Back_Left",
        "Ramp_connection_offset": 24
    }
    "Stairs": {
        Stair1: {
        stair_width: 48,
        "Ramp_connection_side": "Front",
        "Ramp_connection_corner": "Front_left",
        "Ramp_connection_offset": 24
        }

    
    }
}
"""




